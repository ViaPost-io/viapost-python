from __future__ import annotations

import json
import pickle
from typing import cast

import httpx
import pytest

from viapost import (
    AsyncViaPost,
    CreateSuppressionRequest,
    ReleaseSuppressionRequest,
    UpdateWebhookRequest,
    ViaPost,
    ViaPostAPIError,
)


def _webhook_endpoint() -> dict[str, object]:
    return {
        "id": "webhook",
        "url": "https://hooks.example.com/v1",
        "event_types": ["delivered"],
        "enabled": True,
        "max_attempts": 8,
        "consecutive_failures": 0,
        "disabled_at": None,
        "secret_rotated_at": None,
        "version": 1,
        "created_at": "2026-09-16T00:00:00Z",
        "updated_at": "2026-09-16T00:00:00Z",
    }


def test_new_request_typed_dicts_match_the_openapi_required_fields() -> None:
    assert CreateSuppressionRequest.__required_keys__ == frozenset({"email", "reason"})
    assert ReleaseSuppressionRequest.__required_keys__ == frozenset(
        {"expected_version", "acknowledge", "justification"}
    )
    assert UpdateWebhookRequest.__required_keys__ == frozenset({"expected_version"})


def test_sync_webhook_secret_results_require_explicit_access_and_redact_common_rendering() -> None:
    endpoint = _webhook_endpoint()
    endpoint["debug"] = {"token": "endpoint-token"}
    secrets = iter(("whsec-create", "whsec-rotate"))

    def handler(request: httpx.Request) -> httpx.Response:
        secret = next(secrets)
        payload: dict[str, object] = {"endpoint": endpoint, "secret": secret}
        if request.url.path.endswith("/secret/rotate"):
            payload["rotated_at"] = "2026-09-16T01:00:00Z"
        return httpx.Response(200, json=payload)

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        created = client.webhooks.create(
            {"url": "https://hooks.example.com/v1", "event_types": ["delivered"]}
        )
        rotated = client.webhooks.rotate_secret("webhook", idempotency_key="rotate")

    assert created.secret == "whsec-create"
    assert rotated.secret == "whsec-rotate"
    assert created.endpoint["id"] == "webhook"
    assert rotated.rotated_at == "2026-09-16T01:00:00Z"
    for value, secret in ((created, "whsec-create"), (rotated, "whsec-rotate")):
        assert secret not in repr(value)
        assert secret not in str(value)
        assert secret not in json.dumps(value.to_dict())
        assert secret.encode() not in pickle.dumps(value)
        assert "endpoint-token" not in repr(value)
        assert "endpoint-token" not in json.dumps(value.to_dict())
        assert b"endpoint-token" not in pickle.dumps(value)
        assert value.to_dict()["secret"] == "<redacted>"


@pytest.mark.asyncio
async def test_async_webhook_secret_result_is_redacted_too() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"endpoint": _webhook_endpoint(), "secret": "async-secret"})

    async with AsyncViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        result = await client.webhooks.create(
            {"url": "https://hooks.example.com/v1", "event_types": ["delivered"]}
        )
    assert result.secret == "async-secret"
    assert "async-secret" not in repr(result)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@hooks.example.com/path",
        "https://hooks.example.com/path#secret",
        "https://localhost/hook",
        "https://api.localhost/hook",
        "https://127.0.0.1/hook",
        "https://127.1/hook",
        "https://2130706433/hook",
        "https://0x7f000001/hook",
        "https://10.0.0.1/hook",
        "https://169.254.1.1/hook",
        "https://0.0.0.0/hook",
        "https://224.0.0.1/hook",
        "https://[::1]/hook",
    ],
)
def test_webhook_create_rejects_unsafe_callback_urls_without_network(url: str) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ValueError, match="public absolute HTTPS"),
    ):
        client.webhooks.create({"url": url, "event_types": ["delivered"]})
    assert called is False


def test_sync_raw_suppressions_and_webhook_operations_match_the_contract() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        if request.url.path.endswith("/raw"):
            return httpx.Response(200, content=b"From: sender@example.com\r\n\r\nbody")
        if request.url.path == "/v1/suppressions/export":
            return httpx.Response(200, content=b"email,reason\n")
        if request.url.path.endswith("/secret/rotate"):
            return httpx.Response(
                200,
                json={
                    "endpoint": _webhook_endpoint(),
                    "rotated_at": "2026-09-16T01:00:00Z",
                    "secret": "rotate-secret",
                },
            )
        return httpx.Response(200, json={})

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        assert client.messages.raw("m") == b"From: sender@example.com\r\n\r\nbody"
        client.inbound_messages.list({"has_attachments": True})
        client.inbound_messages.retrieve("inbound")
        assert client.inbound_messages.raw("inbound").startswith(b"From:")
        client.suppressions.list({"state": "active"})
        client.suppressions.create({"email": "person@example.com", "reason": "manual"})
        client.suppressions.retrieve("suppression", {"history_limit": 10})
        client.suppressions.release(
            "suppression",
            {"expected_version": 1, "acknowledge": True, "justification": "Customer request"},
        )
        client.suppressions.import_csv(
            "email,reason,expires_at,note\nperson@example.com,manual,,\n"
        )
        assert client.suppressions.export_csv({"state": "active"}) == b"email,reason\n"
        client.webhooks.update("webhook", {"expected_version": 1, "enabled": False})
        client.webhooks.deliveries("webhook", {"limit": 25})
        client.webhooks.delivery("webhook", "delivery")
        client.webhooks.replay("webhook", "delivery", idempotency_key="replay-1")
        client.webhooks.rotate_secret("webhook", idempotency_key="rotate-1")
        client.webhooks.test("webhook", idempotency_key="test-1")

    assert [(request.method, request.url.path) for request in observed] == [
        ("GET", "/v1/messages/m/raw"),
        ("GET", "/v1/inbound-messages"),
        ("GET", "/v1/inbound-messages/inbound"),
        ("GET", "/v1/inbound-messages/inbound/raw"),
        ("GET", "/v1/suppressions"),
        ("POST", "/v1/suppressions"),
        ("GET", "/v1/suppressions/suppression"),
        ("POST", "/v1/suppressions/suppression/release"),
        ("POST", "/v1/suppressions/import"),
        ("GET", "/v1/suppressions/export"),
        ("PATCH", "/v1/webhooks/webhook"),
        ("GET", "/v1/webhooks/webhook/deliveries"),
        ("GET", "/v1/webhooks/webhook/deliveries/delivery"),
        ("POST", "/v1/webhooks/webhook/deliveries/delivery/replay"),
        ("POST", "/v1/webhooks/webhook/secret/rotate"),
        ("POST", "/v1/webhooks/webhook/test"),
    ]
    assert observed[0].headers["Accept"] == "message/rfc822"
    assert observed[8].headers["Content-Type"] == "text/csv; charset=utf-8"
    assert observed[9].headers["Accept"] == "text/csv"
    for index in (13, 14, 15):
        assert observed[index].headers["Idempotency-Key"]
        assert json.loads(observed[index].content) == {}


@pytest.mark.asyncio
async def test_async_new_resources_match_sync_resource_methods() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/raw") or request.url.path.endswith("/export"):
            return httpx.Response(200, content=b"raw")
        return httpx.Response(200, json={})

    sync = ViaPost(api_key="vp_test", transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    async with AsyncViaPost(
        api_key="vp_test", transport=httpx.MockTransport(handler)
    ) as async_client:
        for name in ("inbound_messages", "suppressions"):
            assert {
                method for method in dir(getattr(async_client, name)) if not method.startswith("_")
            } == {method for method in dir(getattr(sync, name)) if not method.startswith("_")}
        assert await async_client.messages.raw("message") == b"raw"
        assert await async_client.inbound_messages.raw("message") == b"raw"
        assert await async_client.suppressions.export_csv() == b"raw"
        await async_client.webhooks.replay("w", "d", idempotency_key="retry")
    sync.close()


@pytest.mark.parametrize(
    ("operation", "payload", "message"),
    [
        ("update", {"expected_version": 0, "enabled": False}, "at least 1"),
        ("update", {"expected_version": 1}, "at least one field"),
        ("update", {"expected_version": 1, "event_types": []}, "at least one item"),
        ("update", {"expected_version": 1, "max_attempts": 21}, "between 1 and 20"),
        (
            "release",
            {"expected_version": 1, "acknowledge": False, "justification": "Customer request"},
            "acknowledge",
        ),
        (
            "release",
            {"expected_version": 0, "acknowledge": True, "justification": "Customer request"},
            "at least 1",
        ),
        (
            "release",
            {"expected_version": 1, "acknowledge": True, "justification": "short"},
            "between 10 and 500",
        ),
    ],
)
def test_new_mutation_constraints_are_rejected_before_network(
    operation: str, payload: dict[str, object], message: str
) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ValueError, match=message),
    ):
        if operation == "update":
            client.webhooks.update("webhook", cast(UpdateWebhookRequest, payload))
        else:
            client.suppressions.release("suppression", cast(ReleaseSuppressionRequest, payload))
    assert called is False


def test_csv_size_and_required_webhook_idempotency_are_validated_before_network() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="2 MiB"):
            client.suppressions.import_csv(b"x" * (2 * 1024 * 1024 + 1))
        with pytest.raises(ValueError, match="idempotency_key"):
            client.webhooks.test("webhook", idempotency_key="unsafe key")
    assert called is False


def test_raw_download_preserves_structured_api_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "forbidden"}})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ViaPostAPIError, match="forbidden") as caught,
    ):
        client.messages.raw("message")

    assert caught.value.status == 403
