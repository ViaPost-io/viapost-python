from __future__ import annotations

import gzip
from typing import cast

import httpx
import pytest
import respx

from viapost import (
    AsyncViaPost,
    ViaPost,
    ViaPostAPIError,
    ViaPostConnectionError,
    ViaPostResponseTooLargeError,
    ViaPostTimeoutError,
)


def test_sync_request_sends_auth_query_headers_and_default_timeout() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["request"] = request
        observed["timeout"] = request.extensions["timeout"]
        return httpx.Response(200, json={"data": [], "meta": {}})

    with ViaPost(api_key="  vp_test  ", transport=httpx.MockTransport(handler)) as client:
        result = client.messages.list({"page": 2, "status": ["queued", "sent"], "none": None})

    request = observed["request"]
    assert isinstance(request, httpx.Request)
    assert request.headers["Authorization"] == "Bearer vp_test"
    assert request.headers["Accept"] == "application/json"
    assert request.headers["User-Agent"] == "viapost-python/0.2.0"
    assert request.url.params.get_list("status") == ["queued", "sent"]
    assert request.url.params["page"] == "2"
    assert "none" not in request.url.params
    assert observed["timeout"] == {"connect": 60.0, "read": 60.0, "write": 60.0, "pool": 60.0}
    assert result == {"data": [], "meta": {}}


@pytest.mark.asyncio
async def test_async_request_has_equivalent_wire_behavior() -> None:
    observed: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json={"data": []})

    async with AsyncViaPost(api_key="vp_async", transport=httpx.MockTransport(handler)) as client:
        result = await client.messages.list({"page": 3})

    assert result == {"data": []}
    assert observed[0].headers["Authorization"] == "Bearer vp_async"
    assert observed[0].url == "https://api.viapost.io/v1/messages?page=3"


def test_api_error_exposes_status_request_id_body_and_request_context() -> None:
    body = {"error": {"message": "not found", "request_id": "body-id"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=body, headers={"x-request-id": "header-id"})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ViaPostAPIError, match="not found") as caught,
    ):
        client.messages.retrieve("msg-1")

    error = caught.value
    assert error.status == 404
    assert error.request_id == "header-id"
    assert error.body == body
    assert error.method == "GET"
    assert error.url == "https://api.viapost.io/v1/messages/msg-1"
    assert error.headers["x-request-id"] == "header-id"


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (httpx.ReadTimeout("slow"), ViaPostTimeoutError),
        (httpx.ConnectError("offline"), ViaPostConnectionError),
    ],
)
def test_transport_failures_are_typed(raised: Exception, expected: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise raised

    with (
        ViaPost(api_key="vp_test", timeout=1.5, transport=httpx.MockTransport(handler)) as client,
        pytest.raises(expected) as caught,
    ):
        client.messages.list()
    if isinstance(caught.value, ViaPostTimeoutError):
        assert caught.value.timeout == 1.5
    if isinstance(caught.value, ViaPostConnectionError):
        assert not hasattr(caught.value, "cause")
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_response_body_limit_is_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"123456")

    with (
        ViaPost(
            api_key="vp_test", max_response_bytes=5, transport=httpx.MockTransport(handler)
        ) as client,
        pytest.raises(ViaPostResponseTooLargeError) as caught,
    ):
        client.messages.list()
    assert caught.value.max_response_bytes == 5
    assert not isinstance(caught.value, ViaPostConnectionError)


def test_compressed_content_length_is_not_compared_with_decoded_limit() -> None:
    encoded = gzip.compress(b"{}")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=encoded,
            headers={"content-encoding": "gzip", "content-length": str(len(encoded))},
        )

    with ViaPost(
        api_key="vp_test", max_response_bytes=5, transport=httpx.MockTransport(handler)
    ) as client:
        assert cast(object, client.messages.list()) == {}


def test_protected_headers_cannot_be_overridden() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json={})

    with ViaPost(api_key="real-key", transport=httpx.MockTransport(handler)) as client:
        client._http.request(
            "GET",
            "/v1/messages",
            headers={
                "authorization": "Bearer attacker",
                "accept": "text/plain",
                "user-agent": "attacker",
            },
        )

    assert observed[0].headers["Authorization"] == "Bearer real-key"
    assert observed[0].headers["Accept"] == "application/json"
    assert observed[0].headers["User-Agent"] == "viapost-python/0.2.0"


def test_api_error_redacts_echoed_credentials_and_sensitive_fields() -> None:
    api_key = "vp_live_do-not-log"
    body = {
        "error": {
            "message": f"invalid credential {api_key}",
            "details": {
                "api_key": api_key,
                "secret": "whsec-do-not-log",
                "nested": [{"access_token": "token-do-not-log"}],
                "safe": "validation failed",
            },
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json=body,
            headers={"set-cookie": "session=do-not-log", "x-debug": api_key},
        )

    with (
        ViaPost(api_key=api_key, transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ViaPostAPIError) as caught,
    ):
        client.messages.list()

    rendered = (
        repr(caught.value)
        + str(caught.value)
        + repr(caught.value.body)
        + repr(caught.value.headers)
    )
    for secret in (api_key, "whsec-do-not-log", "token-do-not-log", "session=do-not-log"):
        assert secret not in rendered
    assert caught.value.body["error"]["details"]["safe"] == "validation failed"  # type: ignore[index]


def test_api_error_redacts_repeated_sensitive_values_from_message_and_debug() -> None:
    repeated = "sensitive-value-repeated-in-diagnostic-text"
    body = {
        "error": {
            "message": f"request denied; token={repeated}; retry token={repeated}",
            "debug": f"secret={repeated}; api_key={repeated}",
            "details": {"access_token": repeated},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json=body)

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ViaPostAPIError) as caught,
    ):
        client.messages.list()

    rendered = repr(caught.value) + str(caught.value) + repr(caught.value.body)
    assert repeated not in rendered
    assert "<redacted>" in str(caught.value)


def test_raw_response_uses_independent_40_mib_default_limit() -> None:
    payload = b"x" * (10 * 1024 * 1024 + 1)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        assert client._config.max_raw_response_bytes == 40 * 1024 * 1024
        assert client.messages.raw("large") == payload


def test_raw_response_limit_is_configurable_without_raising_json_error_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/raw"):
            return httpx.Response(200, content=b"123456")
        return httpx.Response(403, json={"error": {"message": "no"}})

    with ViaPost(
        api_key="vp_test",
        max_response_bytes=64,
        max_raw_response_bytes=5,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(ViaPostResponseTooLargeError) as caught:
            client.messages.raw("large")
        assert caught.value.max_response_bytes == 5
        with pytest.raises(ViaPostAPIError, match="no"):
            client.messages.list()


@pytest.mark.parametrize("status", [103, 302])
def test_informational_and_redirect_responses_are_typed_errors_without_following(
    status: int,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, headers={"location": "https://attacker.example/steal"})

    with (
        ViaPost(api_key="vp_secret", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ViaPostAPIError) as caught,
    ):
        client.messages.list()

    assert caught.value.status == status
    assert [request.url.host for request in requests] == ["api.viapost.io"]


def test_get_retries_429_and_5xx_then_returns_success() -> None:
    statuses = iter([429, 503, 200])
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        status = next(statuses)
        return httpx.Response(status, json={"ok": status == 200}, headers={"retry-after": "0"})

    with ViaPost(
        api_key="vp_test",
        max_retries=2,
        base_delay=0,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.messages.list()

    assert attempts == 3
    assert cast(object, result) == {"ok": True}


@respx.mock
def test_respx_consumer_mocking_is_supported() -> None:
    route = respx.get("https://api.viapost.io/v1/usage").mock(
        return_value=httpx.Response(
            200,
            json={
                "period": {"start": "2026-09-01", "end": "2026-10-01", "timezone": "UTC"},
                "used": 12,
                "limit": 100,
                "remaining": 88,
                "unlimited": False,
            },
        )
    )
    with ViaPost(api_key="vp_test") as client:
        assert client.usage.retrieve()["remaining"] == 88
    assert route.called


@pytest.mark.asyncio
async def test_async_retry_and_typed_failures_match_sync_client() -> None:
    attempts = 0

    async def retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": "retry"}, headers={"retry-after": "0"})
        return httpx.Response(200, json={"ok": True})

    async with AsyncViaPost(
        api_key="vp_test", transport=httpx.MockTransport(retry_handler)
    ) as client:
        assert cast(object, await client.messages.list()) == {"ok": True}
    assert attempts == 2

    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async with AsyncViaPost(
        api_key="vp_test", timeout=2, transport=httpx.MockTransport(timeout_handler)
    ) as client:
        with pytest.raises(ViaPostTimeoutError) as timeout_caught:
            await client.messages.list()
    assert timeout_caught.value.timeout == 2
    assert timeout_caught.value.__cause__ is None
    assert timeout_caught.value.__context__ is None

    async def connection_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async with AsyncViaPost(
        api_key="vp_test", transport=httpx.MockTransport(connection_handler)
    ) as client:
        with pytest.raises(ViaPostConnectionError) as connection_caught:
            await client.messages.list()
    assert connection_caught.value.__cause__ is None
    assert connection_caught.value.__context__ is None

    async def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"error": {"message": "invalid", "request_id": "async-id"}})

    async with AsyncViaPost(
        api_key="vp_test", transport=httpx.MockTransport(error_handler)
    ) as client:
        with pytest.raises(ViaPostAPIError) as api_caught:
            await client.messages.list()
    assert api_caught.value.request_id == "async-id"
