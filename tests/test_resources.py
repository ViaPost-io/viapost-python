from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, cast, get_type_hints

import httpx
import pytest

from viapost import (
    AsyncViaPost,
    CreateAutomationRequest,
    CreateDomainRequest,
    CreateTemplateAssetRequest,
    CreateTemplateRequest,
    CreateWebhookRequest,
    SendRequest,
    UpdateAutomationDraftRequest,
    UpdateTemplateDraftRequest,
    ViaPost,
    ViaPostAPIError,
)


def test_send_forwards_idempotency_key_normalizes_lists_and_never_retries_post() -> None:
    attempts: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json={"accepted": None, "rejected": None})

    with (
        ViaPost(api_key="vp_test", max_retries=2, transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ViaPostAPIError) as caught,
    ):
        client.send.create(
            {"from": "hello@example.com", "to": ["person@example.com"], "subject": "Hi"},
            idempotency_key="order-123",
        )

    assert caught.value.status == 503
    assert len(attempts) == 1
    assert attempts[0].headers["Idempotency-Key"] == "order-123"
    assert attempts[0].headers["Content-Type"] == "application/json"
    assert json.loads(attempts[0].content) == {
        "from": "hello@example.com",
        "to": ["person@example.com"],
        "subject": "Hi",
    }

    def success(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"accepted": None, "rejected": None})

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(success)) as client:
        assert client.send.create({"from": "a", "to": ["b"], "subject": "c"}) == {
            "accepted": [],
            "rejected": [],
        }


def test_path_parameters_are_encoded_and_ambiguous_values_rejected() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        client.messages.retrieve("part/../value ?#")
        for invalid in ("", ".", ".."):
            with pytest.raises(ValueError, match="safe path value"):
                client.messages.retrieve(invalid)

    assert requests[0].url.raw_path == b"/v1/messages/part%2F..%2Fvalue%20%3F%23"


@pytest.mark.parametrize(
    "key", ["", "x" * 256, "line\nbreak", "hidden\u200bformat", "café", "has space", 123]
)
def test_send_rejects_unsafe_idempotency_keys_before_network(key: object) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ValueError, match="idempotency_key"),
    ):
        client.send.create({"from": "a", "to": ["b"]}, idempotency_key=cast(str, key))
    assert called is False


@pytest.mark.parametrize(
    ("resource", "payload", "message"),
    [
        ("send", {"from": "a", "to": []}, "between 1 and 50"),
        ("send", {"from": "a", "to": ["b"] * 51}, "between 1 and 50"),
        ("send", {"from": "a", "to": ["b"], "cc": ["c"] * 51}, "at most 50"),
        (
            "send",
            {"from": "a", "to": ["b"], "variables": {str(i): i for i in range(101)}},
            "at most 100",
        ),
        ("send", {"from": "a", "to": ["b"], "attachments": [{}] * 11}, "at most 10"),
        ("webhooks", {"url": "file:///tmp/hook", "event_types": ["delivered"]}, "HTTP\\(S\\)"),
        ("webhooks", {"url": "https://example.com/hook", "event_types": []}, "at least one"),
    ],
)
def test_critical_openapi_constraints_are_rejected_before_network(
    resource: str, payload: dict[str, object], message: str
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
        if resource == "send":
            client.send.create(cast(SendRequest, payload))
        else:
            client.webhooks.create(cast(CreateWebhookRequest, payload))
    assert called is False


@pytest.mark.parametrize(
    "payload",
    [
        {"content_json": {}, "variables": [{}] * 101},
        {"content_json": {}, "variables": [], "expected_version_id": "version"},
        {"content_json": {}, "variables": [], "expected_updated_at": "2026-09-11T00:00:00Z"},
    ],
)
def test_template_draft_constraints_are_rejected_before_network(
    payload: dict[str, object],
) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ValueError),
    ):
        client.templates.update_draft("template", cast(UpdateTemplateDraftRequest, payload))
    assert called is False


def test_template_preview_rejects_more_than_one_hundred_variables_before_network() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with (
        ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ValueError, match="at most 100"),
    ):
        client.templates.preview("template", {"variables": {str(i): i for i in range(101)}})
    assert called is False


def test_request_typed_dicts_match_openapi_required_fields() -> None:
    assert SendRequest.__required_keys__ == frozenset({"from", "to"})
    assert CreateDomainRequest.__required_keys__ == frozenset({"name"})
    assert CreateTemplateRequest.__required_keys__ == frozenset({"name"})
    assert CreateTemplateAssetRequest.__required_keys__ == frozenset({"filename", "content_type"})
    assert CreateWebhookRequest.__required_keys__ == frozenset({"url", "event_types"})
    assert CreateAutomationRequest.__required_keys__ == frozenset({"name"})
    assert UpdateAutomationDraftRequest.__required_keys__ == frozenset({"graph"})
    assert UpdateTemplateDraftRequest.__required_keys__ == frozenset({"content_json", "variables"})


def test_public_resource_methods_never_return_any() -> None:
    sync = ViaPost(api_key="vp_test", transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    async_client = AsyncViaPost(
        api_key="vp_test", transport=httpx.MockTransport(lambda r: httpx.Response(200))
    )
    for client in (sync, async_client):
        for resource_name in (
            "send",
            "messages",
            "domains",
            "templates",
            "webhooks",
            "automations",
            "usage",
        ):
            resource = getattr(client, resource_name)
            for method_name, method in inspect.getmembers(resource, predicate=callable):
                if method_name.startswith("_"):
                    continue
                assert get_type_hints(method)["return"] is not Any
    sync.close()
    asyncio.run(async_client.aclose())


def test_sync_resources_cover_the_public_node_sdk_surface() -> None:
    observed: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append((request.method, request.url.path))
        return httpx.Response(200, json={})

    with ViaPost(api_key="vp_test", transport=httpx.MockTransport(handler)) as client:
        client.messages.events("m")
        client.messages.engagement({"days": 7})
        client.messages.metrics()
        client.messages.timeseries()
        client.domains.list()
        client.domains.create({"name": "example.com"})
        client.domains.retrieve("d")
        client.domains.delete("d")
        client.domains.dns("d")
        client.domains.verify("d")
        client.domains.rotate_dkim("d")
        client.templates.list()
        client.templates.create({"name": "welcome"})
        client.templates.retrieve("t")
        client.templates.delete("t")
        client.templates.archive("t")
        client.templates.create_asset("t", {"filename": "hero.png", "content_type": "image/png"})
        client.templates.update_draft("t", {"content_json": {}, "variables": [], "subject": "Hi"})
        client.templates.duplicate("t")
        client.templates.preview("t", {"variables": {}})
        client.templates.publish("t", {})
        client.templates.versions("t")
        client.templates.version("t", "v")
        client.templates.revert("t", "v", {})
        client.webhooks.list()
        client.webhooks.create({"url": "https://example.com/hook", "event_types": ["delivered"]})
        client.webhooks.delete("w")
        client.automations.list()
        client.automations.create({"name": "onboarding"})
        client.automations.retrieve("a")
        client.automations.update("a", {"name": "updated"})
        client.automations.delete("a")
        client.automations.activate("a")
        client.automations.disable("a")
        client.automations.update_draft("a", {"graph": {}})
        client.automations.duplicate("a")
        client.automations.runs("a")
        client.automations.run("a", "r")
        client.automations.cancel_run("a", "r")
        client.usage.retrieve()

    assert observed == [
        ("GET", "/v1/messages/m/events"),
        ("GET", "/v1/messages/engagement"),
        ("GET", "/v1/messages/metrics"),
        ("GET", "/v1/messages/timeseries"),
        ("GET", "/v1/domains"),
        ("POST", "/v1/domains"),
        ("GET", "/v1/domains/d"),
        ("DELETE", "/v1/domains/d"),
        ("GET", "/v1/domains/d/dns"),
        ("POST", "/v1/domains/d/verify"),
        ("POST", "/v1/domains/d/dkim/rotate"),
        ("GET", "/v1/templates"),
        ("POST", "/v1/templates"),
        ("GET", "/v1/templates/t"),
        ("DELETE", "/v1/templates/t"),
        ("POST", "/v1/templates/t/archive"),
        ("POST", "/v1/templates/t/assets"),
        ("PATCH", "/v1/templates/t/draft"),
        ("POST", "/v1/templates/t/duplicate"),
        ("POST", "/v1/templates/t/preview"),
        ("POST", "/v1/templates/t/publish"),
        ("GET", "/v1/templates/t/versions"),
        ("GET", "/v1/templates/t/versions/v"),
        ("POST", "/v1/templates/t/versions/v/revert"),
        ("GET", "/v1/webhooks"),
        ("POST", "/v1/webhooks"),
        ("DELETE", "/v1/webhooks/w"),
        ("GET", "/v1/automations"),
        ("POST", "/v1/automations"),
        ("GET", "/v1/automations/a"),
        ("PATCH", "/v1/automations/a"),
        ("DELETE", "/v1/automations/a"),
        ("POST", "/v1/automations/a/activate"),
        ("POST", "/v1/automations/a/disable"),
        ("PATCH", "/v1/automations/a/draft"),
        ("POST", "/v1/automations/a/duplicate"),
        ("GET", "/v1/automations/a/runs"),
        ("GET", "/v1/automations/a/runs/r"),
        ("POST", "/v1/automations/a/runs/r/cancel"),
        ("GET", "/v1/usage"),
    ]


@pytest.mark.asyncio
async def test_async_resources_match_sync_resource_methods() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"accepted": [], "rejected": []})

    sync = ViaPost(api_key="vp_test", transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    async with AsyncViaPost(
        api_key="vp_test", transport=httpx.MockTransport(handler)
    ) as async_client:
        resource_names = (
            "send",
            "messages",
            "domains",
            "templates",
            "webhooks",
            "automations",
            "usage",
        )
        for name in resource_names:
            sync_methods = {
                method
                for method, value in inspect.getmembers(getattr(sync, name), predicate=callable)
                if not method.startswith("_")
            }
            async_methods = {
                method
                for method, value in inspect.getmembers(
                    getattr(async_client, name), predicate=callable
                )
                if not method.startswith("_")
            }
            assert async_methods == sync_methods

        assert cast(object, await async_client.domains.retrieve("domain")) == {
            "accepted": [],
            "rejected": [],
        }
        assert cast(object, await async_client.templates.version("template", "version")) == {
            "accepted": [],
            "rejected": [],
        }
        await async_client.automations.cancel_run("automation", "run")
        assert cast(object, await async_client.usage.retrieve()) == {
            "accepted": [],
            "rejected": [],
        }
        await async_client.send.create({"from": "a", "to": ["b"]}, idempotency_key="key")
        await async_client.messages.list()
        await async_client.messages.retrieve("m")
        await async_client.messages.events("m")
        await async_client.messages.engagement()
        await async_client.messages.metrics()
        await async_client.messages.timeseries()
        await async_client.domains.list()
        await async_client.domains.create({"name": "example.com"})
        await async_client.domains.delete("d")
        await async_client.domains.dns("d")
        await async_client.domains.verify("d")
        await async_client.domains.rotate_dkim("d")
        await async_client.templates.list()
        await async_client.templates.create({"name": "welcome"})
        await async_client.templates.retrieve("t")
        await async_client.templates.delete("t")
        await async_client.templates.archive("t")
        await async_client.templates.create_asset(
            "t", {"filename": "asset", "content_type": "image/png"}
        )
        await async_client.templates.update_draft("t", {"content_json": {}, "variables": []})
        await async_client.templates.duplicate("t")
        await async_client.templates.preview("t", {})
        await async_client.templates.publish("t")
        await async_client.templates.versions("t")
        await async_client.templates.revert("t", "v")
        await async_client.webhooks.list()
        await async_client.webhooks.create(
            {"url": "https://example.com", "event_types": ["delivered"]}
        )
        await async_client.webhooks.delete("w")
        await async_client.automations.list()
        await async_client.automations.create({"name": "auto"})
        await async_client.automations.retrieve("a")
        await async_client.automations.update("a", {"name": "updated"})
        await async_client.automations.delete("a")
        await async_client.automations.activate("a")
        await async_client.automations.disable("a")
        await async_client.automations.update_draft("a", {"graph": {}})
        await async_client.automations.duplicate("a")
        await async_client.automations.runs("a")
        await async_client.automations.run("a", "r")
    sync.close()
