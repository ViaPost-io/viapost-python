"""Typed synchronous and asynchronous ViaPost API resources."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from typing import cast
from urllib.parse import quote, urlsplit

from ._http import AsyncHTTPClient, SyncHTTPClient
from .types import (
    AcceptedMessage,
    Automation,
    AutomationList,
    AutomationRunDetail,
    AutomationRunList,
    CreateAutomationRequest,
    CreateDomainRequest,
    CreateDomainResponse,
    CreateTemplateAssetRequest,
    CreateTemplateRequest,
    CreateTemplateResponse,
    CreateWebhookRequest,
    CreateWebhookResponse,
    DNSRecordList,
    Domain,
    DomainList,
    EmailTemplate,
    EmailTemplateVersion,
    EngagementResponse,
    Message,
    MessageEventList,
    MessageList,
    MetricsResponse,
    MonthlyUsage,
    PreviewTemplateRequest,
    PreviewTemplateResponse,
    QueryValue,
    RejectedMessage,
    RenameAutomationRequest,
    RotateDKIMResponse,
    SendRequest,
    SendResult,
    TemplateAssetPolicy,
    TemplateList,
    TemplatePreconditionRequest,
    TemplateVersionList,
    TimeseriesResponse,
    UpdateAutomationDraftRequest,
    UpdateTemplateDraftRequest,
    UpdateTemplateDraftResponse,
    WebhookList,
)

QueryInput = Mapping[str, QueryValue]


def _validate_idempotency_key(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("idempotency_key must be a header-safe visible ASCII string")
    length = len(value.encode("utf-8"))
    if length == 0 or length > 255:
        raise ValueError("idempotency_key must contain between 1 and 255 UTF-8 bytes")
    if any(unicodedata.category(char) in {"Cc", "Cf"} for char in value):
        raise ValueError("idempotency_key must not contain Unicode control or format characters")
    if any(ord(char) < 0x21 or ord(char) > 0x7E for char in value):
        raise ValueError("idempotency_key must contain only header-safe visible ASCII characters")


def _path_param(name: str, value: str) -> str:
    if value in {"", ".", ".."}:
        raise ValueError(f"{name} must be a non-empty safe path value other than '.' or '..'")
    return quote(value, safe="")


def _validate_send_request(value: SendRequest) -> None:
    recipients = value.get("to", [])
    if not 1 <= len(recipients) <= 50:
        raise ValueError("to must contain between 1 and 50 recipients")
    for field in ("cc", "bcc"):
        if len(cast(list[str], value.get(field, []))) > 50:
            raise ValueError(f"{field} must contain at most 50 recipients")
    if len(value.get("variables", {})) > 100:
        raise ValueError("variables must contain at most 100 properties")
    if len(value.get("attachments", [])) > 10:
        raise ValueError("attachments must contain at most 10 items")


def _validate_template_draft(value: UpdateTemplateDraftRequest) -> None:
    if len(value.get("variables", [])) > 100:
        raise ValueError("variables must contain at most 100 items")
    has_version = "expected_version_id" in value
    has_updated_at = "expected_updated_at" in value
    if has_version != has_updated_at:
        raise ValueError("expected_version_id and expected_updated_at must be provided together")


def _validate_preview(value: PreviewTemplateRequest) -> None:
    if len(value.get("variables", {})) > 100:
        raise ValueError("variables must contain at most 100 properties")


def _validate_webhook(value: CreateWebhookRequest) -> None:
    parsed = urlsplit(value.get("url", ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be an absolute HTTP(S) URL")
    if not value.get("event_types"):
        raise ValueError("event_types must contain at least one item")


def _send_result(value: object) -> SendResult:
    raw = cast(dict[str, object], value)
    return {
        "accepted": cast(list[AcceptedMessage], raw.get("accepted") or []),
        "rejected": cast(list[RejectedMessage], raw.get("rejected") or []),
    }


class SendResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def create(
        self,
        input: SendRequest,
        *,
        idempotency_key: str | None = None,
        timeout: float | None = None,
    ) -> SendResult:
        _validate_send_request(input)
        headers = None
        if idempotency_key is not None:
            _validate_idempotency_key(idempotency_key)
            headers = {"Idempotency-Key": idempotency_key}
        return _send_result(
            self._http.request("POST", "/v1/send", body=input, headers=headers, timeout=timeout)
        )


class AsyncSendResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def create(
        self,
        input: SendRequest,
        *,
        idempotency_key: str | None = None,
        timeout: float | None = None,
    ) -> SendResult:
        _validate_send_request(input)
        headers = None
        if idempotency_key is not None:
            _validate_idempotency_key(idempotency_key)
            headers = {"Idempotency-Key": idempotency_key}
        return _send_result(
            await self._http.request(
                "POST", "/v1/send", body=input, headers=headers, timeout=timeout
            )
        )


class MessagesResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def list(self, query: QueryInput | None = None, *, timeout: float | None = None) -> MessageList:
        return cast(
            MessageList, self._http.request("GET", "/v1/messages", query=query, timeout=timeout)
        )

    def retrieve(self, message_id: str, *, timeout: float | None = None) -> Message:
        mid = _path_param("message_id", message_id)
        return cast(Message, self._http.request("GET", f"/v1/messages/{mid}", timeout=timeout))

    def events(self, message_id: str, *, timeout: float | None = None) -> MessageEventList:
        mid = _path_param("message_id", message_id)
        return cast(
            MessageEventList,
            self._http.request("GET", f"/v1/messages/{mid}/events", timeout=timeout),
        )

    def engagement(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> EngagementResponse:
        return cast(
            EngagementResponse,
            self._http.request("GET", "/v1/messages/engagement", query=query, timeout=timeout),
        )

    def metrics(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> MetricsResponse:
        return cast(
            MetricsResponse,
            self._http.request("GET", "/v1/messages/metrics", query=query, timeout=timeout),
        )

    def timeseries(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> TimeseriesResponse:
        return cast(
            TimeseriesResponse,
            self._http.request("GET", "/v1/messages/timeseries", query=query, timeout=timeout),
        )


class DomainsResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def list(self, *, timeout: float | None = None) -> DomainList:
        return cast(DomainList, self._http.request("GET", "/v1/domains", timeout=timeout))

    def create(
        self, input: CreateDomainRequest, *, timeout: float | None = None
    ) -> CreateDomainResponse:
        return cast(
            CreateDomainResponse,
            self._http.request("POST", "/v1/domains", body=input, timeout=timeout),
        )

    def retrieve(self, domain_id: str, *, timeout: float | None = None) -> Domain:
        did = _path_param("domain_id", domain_id)
        return cast(Domain, self._http.request("GET", f"/v1/domains/{did}", timeout=timeout))

    def delete(self, domain_id: str, *, timeout: float | None = None) -> None:
        did = _path_param("domain_id", domain_id)
        self._http.request("DELETE", f"/v1/domains/{did}", timeout=timeout)

    def dns(self, domain_id: str, *, timeout: float | None = None) -> DNSRecordList:
        did = _path_param("domain_id", domain_id)
        return cast(
            DNSRecordList, self._http.request("GET", f"/v1/domains/{did}/dns", timeout=timeout)
        )

    def verify(self, domain_id: str, *, timeout: float | None = None) -> Domain:
        did = _path_param("domain_id", domain_id)
        return cast(
            Domain, self._http.request("POST", f"/v1/domains/{did}/verify", timeout=timeout)
        )

    def rotate_dkim(self, domain_id: str, *, timeout: float | None = None) -> RotateDKIMResponse:
        did = _path_param("domain_id", domain_id)
        return cast(
            RotateDKIMResponse,
            self._http.request("POST", f"/v1/domains/{did}/dkim/rotate", timeout=timeout),
        )


class TemplatesResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def list(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> TemplateList:
        return cast(
            TemplateList, self._http.request("GET", "/v1/templates", query=query, timeout=timeout)
        )

    def create(
        self, input: CreateTemplateRequest, *, timeout: float | None = None
    ) -> CreateTemplateResponse:
        return cast(
            CreateTemplateResponse,
            self._http.request("POST", "/v1/templates", body=input, timeout=timeout),
        )

    def retrieve(self, template_id: str, *, timeout: float | None = None) -> EmailTemplate:
        tid = _path_param("template_id", template_id)
        return cast(
            EmailTemplate, self._http.request("GET", f"/v1/templates/{tid}", timeout=timeout)
        )

    def delete(self, template_id: str, *, timeout: float | None = None) -> None:
        tid = _path_param("template_id", template_id)
        self._http.request("DELETE", f"/v1/templates/{tid}", timeout=timeout)

    def archive(self, template_id: str, *, timeout: float | None = None) -> None:
        tid = _path_param("template_id", template_id)
        self._http.request("POST", f"/v1/templates/{tid}/archive", timeout=timeout)

    def create_asset(
        self, template_id: str, input: CreateTemplateAssetRequest, *, timeout: float | None = None
    ) -> TemplateAssetPolicy:
        tid = _path_param("template_id", template_id)
        return cast(
            TemplateAssetPolicy,
            self._http.request("POST", f"/v1/templates/{tid}/assets", body=input, timeout=timeout),
        )

    def update_draft(
        self, template_id: str, input: UpdateTemplateDraftRequest, *, timeout: float | None = None
    ) -> UpdateTemplateDraftResponse:
        _validate_template_draft(input)
        tid = _path_param("template_id", template_id)
        return cast(
            UpdateTemplateDraftResponse,
            self._http.request("PATCH", f"/v1/templates/{tid}/draft", body=input, timeout=timeout),
        )

    def duplicate(
        self, template_id: str, *, timeout: float | None = None
    ) -> CreateTemplateResponse:
        tid = _path_param("template_id", template_id)
        return cast(
            CreateTemplateResponse,
            self._http.request("POST", f"/v1/templates/{tid}/duplicate", timeout=timeout),
        )

    def preview(
        self, template_id: str, input: PreviewTemplateRequest, *, timeout: float | None = None
    ) -> PreviewTemplateResponse:
        _validate_preview(input)
        tid = _path_param("template_id", template_id)
        return cast(
            PreviewTemplateResponse,
            self._http.request("POST", f"/v1/templates/{tid}/preview", body=input, timeout=timeout),
        )

    def publish(
        self,
        template_id: str,
        input: TemplatePreconditionRequest | None = None,
        *,
        timeout: float | None = None,
    ) -> EmailTemplateVersion:
        tid = _path_param("template_id", template_id)
        return cast(
            EmailTemplateVersion,
            self._http.request("POST", f"/v1/templates/{tid}/publish", body=input, timeout=timeout),
        )

    def versions(self, template_id: str, *, timeout: float | None = None) -> TemplateVersionList:
        tid = _path_param("template_id", template_id)
        return cast(
            TemplateVersionList,
            self._http.request("GET", f"/v1/templates/{tid}/versions", timeout=timeout),
        )

    def version(
        self, template_id: str, version_id: str, *, timeout: float | None = None
    ) -> EmailTemplateVersion:
        tid = _path_param("template_id", template_id)
        vid = _path_param("version_id", version_id)
        return cast(
            EmailTemplateVersion,
            self._http.request("GET", f"/v1/templates/{tid}/versions/{vid}", timeout=timeout),
        )

    def revert(
        self,
        template_id: str,
        version_id: str,
        input: TemplatePreconditionRequest | None = None,
        *,
        timeout: float | None = None,
    ) -> EmailTemplateVersion:
        tid = _path_param("template_id", template_id)
        vid = _path_param("version_id", version_id)
        return cast(
            EmailTemplateVersion,
            self._http.request(
                "POST", f"/v1/templates/{tid}/versions/{vid}/revert", body=input, timeout=timeout
            ),
        )


class WebhooksResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def list(self, *, timeout: float | None = None) -> WebhookList:
        return cast(WebhookList, self._http.request("GET", "/v1/webhooks", timeout=timeout))

    def create(
        self, input: CreateWebhookRequest, *, timeout: float | None = None
    ) -> CreateWebhookResponse:
        _validate_webhook(input)
        return cast(
            CreateWebhookResponse,
            self._http.request("POST", "/v1/webhooks", body=input, timeout=timeout),
        )

    def delete(self, webhook_id: str, *, timeout: float | None = None) -> None:
        wid = _path_param("webhook_id", webhook_id)
        self._http.request("DELETE", f"/v1/webhooks/{wid}", timeout=timeout)


class AutomationsResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def list(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> AutomationList:
        return cast(
            AutomationList,
            self._http.request("GET", "/v1/automations", query=query, timeout=timeout),
        )

    def create(self, input: CreateAutomationRequest, *, timeout: float | None = None) -> Automation:
        return cast(
            Automation, self._http.request("POST", "/v1/automations", body=input, timeout=timeout)
        )

    def retrieve(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation, self._http.request("GET", f"/v1/automations/{aid}", timeout=timeout)
        )

    def update(
        self, automation_id: str, input: RenameAutomationRequest, *, timeout: float | None = None
    ) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            self._http.request("PATCH", f"/v1/automations/{aid}", body=input, timeout=timeout),
        )

    def delete(self, automation_id: str, *, timeout: float | None = None) -> None:
        aid = _path_param("automation_id", automation_id)
        self._http.request("DELETE", f"/v1/automations/{aid}", timeout=timeout)

    def activate(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            self._http.request("POST", f"/v1/automations/{aid}/activate", timeout=timeout),
        )

    def disable(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            self._http.request("POST", f"/v1/automations/{aid}/disable", timeout=timeout),
        )

    def update_draft(
        self,
        automation_id: str,
        input: UpdateAutomationDraftRequest,
        *,
        timeout: float | None = None,
    ) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            self._http.request(
                "PATCH", f"/v1/automations/{aid}/draft", body=input, timeout=timeout
            ),
        )

    def duplicate(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            self._http.request("POST", f"/v1/automations/{aid}/duplicate", timeout=timeout),
        )

    def runs(
        self,
        automation_id: str,
        query: QueryInput | None = None,
        *,
        timeout: float | None = None,
    ) -> AutomationRunList:
        aid = _path_param("automation_id", automation_id)
        return cast(
            AutomationRunList,
            self._http.request("GET", f"/v1/automations/{aid}/runs", query=query, timeout=timeout),
        )

    def run(
        self, automation_id: str, run_id: str, *, timeout: float | None = None
    ) -> AutomationRunDetail:
        aid = _path_param("automation_id", automation_id)
        rid = _path_param("run_id", run_id)
        return cast(
            AutomationRunDetail,
            self._http.request("GET", f"/v1/automations/{aid}/runs/{rid}", timeout=timeout),
        )

    def cancel_run(self, automation_id: str, run_id: str, *, timeout: float | None = None) -> None:
        aid = _path_param("automation_id", automation_id)
        rid = _path_param("run_id", run_id)
        self._http.request("POST", f"/v1/automations/{aid}/runs/{rid}/cancel", timeout=timeout)


class UsageResource:
    def __init__(self, http: SyncHTTPClient) -> None:
        self._http = http

    def retrieve(self, *, timeout: float | None = None) -> MonthlyUsage:
        return cast(MonthlyUsage, self._http.request("GET", "/v1/usage", timeout=timeout))


class AsyncMessagesResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> MessageList:
        return cast(
            MessageList,
            await self._http.request("GET", "/v1/messages", query=query, timeout=timeout),
        )

    async def retrieve(self, message_id: str, *, timeout: float | None = None) -> Message:
        mid = _path_param("message_id", message_id)
        return cast(
            Message, await self._http.request("GET", f"/v1/messages/{mid}", timeout=timeout)
        )

    async def events(self, message_id: str, *, timeout: float | None = None) -> MessageEventList:
        mid = _path_param("message_id", message_id)
        return cast(
            MessageEventList,
            await self._http.request("GET", f"/v1/messages/{mid}/events", timeout=timeout),
        )

    async def engagement(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> EngagementResponse:
        return cast(
            EngagementResponse,
            await self._http.request(
                "GET", "/v1/messages/engagement", query=query, timeout=timeout
            ),
        )

    async def metrics(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> MetricsResponse:
        return cast(
            MetricsResponse,
            await self._http.request("GET", "/v1/messages/metrics", query=query, timeout=timeout),
        )

    async def timeseries(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> TimeseriesResponse:
        return cast(
            TimeseriesResponse,
            await self._http.request(
                "GET", "/v1/messages/timeseries", query=query, timeout=timeout
            ),
        )


class AsyncDomainsResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, *, timeout: float | None = None) -> DomainList:
        return cast(DomainList, await self._http.request("GET", "/v1/domains", timeout=timeout))

    async def create(
        self, input: CreateDomainRequest, *, timeout: float | None = None
    ) -> CreateDomainResponse:
        return cast(
            CreateDomainResponse,
            await self._http.request("POST", "/v1/domains", body=input, timeout=timeout),
        )

    async def retrieve(self, domain_id: str, *, timeout: float | None = None) -> Domain:
        did = _path_param("domain_id", domain_id)
        return cast(Domain, await self._http.request("GET", f"/v1/domains/{did}", timeout=timeout))

    async def delete(self, domain_id: str, *, timeout: float | None = None) -> None:
        did = _path_param("domain_id", domain_id)
        await self._http.request("DELETE", f"/v1/domains/{did}", timeout=timeout)

    async def dns(self, domain_id: str, *, timeout: float | None = None) -> DNSRecordList:
        did = _path_param("domain_id", domain_id)
        return cast(
            DNSRecordList,
            await self._http.request("GET", f"/v1/domains/{did}/dns", timeout=timeout),
        )

    async def verify(self, domain_id: str, *, timeout: float | None = None) -> Domain:
        did = _path_param("domain_id", domain_id)
        return cast(
            Domain, await self._http.request("POST", f"/v1/domains/{did}/verify", timeout=timeout)
        )

    async def rotate_dkim(
        self, domain_id: str, *, timeout: float | None = None
    ) -> RotateDKIMResponse:
        did = _path_param("domain_id", domain_id)
        return cast(
            RotateDKIMResponse,
            await self._http.request("POST", f"/v1/domains/{did}/dkim/rotate", timeout=timeout),
        )


class AsyncTemplatesResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> TemplateList:
        return cast(
            TemplateList,
            await self._http.request("GET", "/v1/templates", query=query, timeout=timeout),
        )

    async def create(
        self, input: CreateTemplateRequest, *, timeout: float | None = None
    ) -> CreateTemplateResponse:
        return cast(
            CreateTemplateResponse,
            await self._http.request("POST", "/v1/templates", body=input, timeout=timeout),
        )

    async def retrieve(self, template_id: str, *, timeout: float | None = None) -> EmailTemplate:
        tid = _path_param("template_id", template_id)
        return cast(
            EmailTemplate, await self._http.request("GET", f"/v1/templates/{tid}", timeout=timeout)
        )

    async def delete(self, template_id: str, *, timeout: float | None = None) -> None:
        tid = _path_param("template_id", template_id)
        await self._http.request("DELETE", f"/v1/templates/{tid}", timeout=timeout)

    async def archive(self, template_id: str, *, timeout: float | None = None) -> None:
        tid = _path_param("template_id", template_id)
        await self._http.request("POST", f"/v1/templates/{tid}/archive", timeout=timeout)

    async def create_asset(
        self, template_id: str, input: CreateTemplateAssetRequest, *, timeout: float | None = None
    ) -> TemplateAssetPolicy:
        tid = _path_param("template_id", template_id)
        return cast(
            TemplateAssetPolicy,
            await self._http.request(
                "POST", f"/v1/templates/{tid}/assets", body=input, timeout=timeout
            ),
        )

    async def update_draft(
        self, template_id: str, input: UpdateTemplateDraftRequest, *, timeout: float | None = None
    ) -> UpdateTemplateDraftResponse:
        _validate_template_draft(input)
        tid = _path_param("template_id", template_id)
        return cast(
            UpdateTemplateDraftResponse,
            await self._http.request(
                "PATCH", f"/v1/templates/{tid}/draft", body=input, timeout=timeout
            ),
        )

    async def duplicate(
        self, template_id: str, *, timeout: float | None = None
    ) -> CreateTemplateResponse:
        tid = _path_param("template_id", template_id)
        return cast(
            CreateTemplateResponse,
            await self._http.request("POST", f"/v1/templates/{tid}/duplicate", timeout=timeout),
        )

    async def preview(
        self, template_id: str, input: PreviewTemplateRequest, *, timeout: float | None = None
    ) -> PreviewTemplateResponse:
        _validate_preview(input)
        tid = _path_param("template_id", template_id)
        return cast(
            PreviewTemplateResponse,
            await self._http.request(
                "POST", f"/v1/templates/{tid}/preview", body=input, timeout=timeout
            ),
        )

    async def publish(
        self,
        template_id: str,
        input: TemplatePreconditionRequest | None = None,
        *,
        timeout: float | None = None,
    ) -> EmailTemplateVersion:
        tid = _path_param("template_id", template_id)
        return cast(
            EmailTemplateVersion,
            await self._http.request(
                "POST", f"/v1/templates/{tid}/publish", body=input, timeout=timeout
            ),
        )

    async def versions(
        self, template_id: str, *, timeout: float | None = None
    ) -> TemplateVersionList:
        tid = _path_param("template_id", template_id)
        return cast(
            TemplateVersionList,
            await self._http.request("GET", f"/v1/templates/{tid}/versions", timeout=timeout),
        )

    async def version(
        self, template_id: str, version_id: str, *, timeout: float | None = None
    ) -> EmailTemplateVersion:
        tid = _path_param("template_id", template_id)
        vid = _path_param("version_id", version_id)
        return cast(
            EmailTemplateVersion,
            await self._http.request("GET", f"/v1/templates/{tid}/versions/{vid}", timeout=timeout),
        )

    async def revert(
        self,
        template_id: str,
        version_id: str,
        input: TemplatePreconditionRequest | None = None,
        *,
        timeout: float | None = None,
    ) -> EmailTemplateVersion:
        tid = _path_param("template_id", template_id)
        vid = _path_param("version_id", version_id)
        return cast(
            EmailTemplateVersion,
            await self._http.request(
                "POST", f"/v1/templates/{tid}/versions/{vid}/revert", body=input, timeout=timeout
            ),
        )


class AsyncWebhooksResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, *, timeout: float | None = None) -> WebhookList:
        return cast(WebhookList, await self._http.request("GET", "/v1/webhooks", timeout=timeout))

    async def create(
        self, input: CreateWebhookRequest, *, timeout: float | None = None
    ) -> CreateWebhookResponse:
        _validate_webhook(input)
        return cast(
            CreateWebhookResponse,
            await self._http.request("POST", "/v1/webhooks", body=input, timeout=timeout),
        )

    async def delete(self, webhook_id: str, *, timeout: float | None = None) -> None:
        wid = _path_param("webhook_id", webhook_id)
        await self._http.request("DELETE", f"/v1/webhooks/{wid}", timeout=timeout)


class AsyncAutomationsResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(
        self, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> AutomationList:
        return cast(
            AutomationList,
            await self._http.request("GET", "/v1/automations", query=query, timeout=timeout),
        )

    async def create(
        self, input: CreateAutomationRequest, *, timeout: float | None = None
    ) -> Automation:
        return cast(
            Automation,
            await self._http.request("POST", "/v1/automations", body=input, timeout=timeout),
        )

    async def retrieve(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation, await self._http.request("GET", f"/v1/automations/{aid}", timeout=timeout)
        )

    async def update(
        self, automation_id: str, input: RenameAutomationRequest, *, timeout: float | None = None
    ) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            await self._http.request(
                "PATCH", f"/v1/automations/{aid}", body=input, timeout=timeout
            ),
        )

    async def delete(self, automation_id: str, *, timeout: float | None = None) -> None:
        aid = _path_param("automation_id", automation_id)
        await self._http.request("DELETE", f"/v1/automations/{aid}", timeout=timeout)

    async def activate(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            await self._http.request("POST", f"/v1/automations/{aid}/activate", timeout=timeout),
        )

    async def disable(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            await self._http.request("POST", f"/v1/automations/{aid}/disable", timeout=timeout),
        )

    async def update_draft(
        self,
        automation_id: str,
        input: UpdateAutomationDraftRequest,
        *,
        timeout: float | None = None,
    ) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            await self._http.request(
                "PATCH", f"/v1/automations/{aid}/draft", body=input, timeout=timeout
            ),
        )

    async def duplicate(self, automation_id: str, *, timeout: float | None = None) -> Automation:
        aid = _path_param("automation_id", automation_id)
        return cast(
            Automation,
            await self._http.request("POST", f"/v1/automations/{aid}/duplicate", timeout=timeout),
        )

    async def runs(
        self, automation_id: str, query: QueryInput | None = None, *, timeout: float | None = None
    ) -> AutomationRunList:
        aid = _path_param("automation_id", automation_id)
        return cast(
            AutomationRunList,
            await self._http.request(
                "GET", f"/v1/automations/{aid}/runs", query=query, timeout=timeout
            ),
        )

    async def run(
        self, automation_id: str, run_id: str, *, timeout: float | None = None
    ) -> AutomationRunDetail:
        aid = _path_param("automation_id", automation_id)
        rid = _path_param("run_id", run_id)
        return cast(
            AutomationRunDetail,
            await self._http.request("GET", f"/v1/automations/{aid}/runs/{rid}", timeout=timeout),
        )

    async def cancel_run(
        self, automation_id: str, run_id: str, *, timeout: float | None = None
    ) -> None:
        aid = _path_param("automation_id", automation_id)
        rid = _path_param("run_id", run_id)
        await self._http.request(
            "POST", f"/v1/automations/{aid}/runs/{rid}/cancel", timeout=timeout
        )


class AsyncUsageResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def retrieve(self, *, timeout: float | None = None) -> MonthlyUsage:
        return cast(MonthlyUsage, await self._http.request("GET", "/v1/usage", timeout=timeout))
