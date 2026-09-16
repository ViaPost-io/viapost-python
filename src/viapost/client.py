"""Public ViaPost clients."""

from __future__ import annotations

from types import TracebackType

import httpx

from ._config import (
    DEFAULT_BASE_DELAY,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_RAW_RESPONSE_BYTES,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    ClientConfig,
    make_config,
)
from ._http import AsyncHTTPClient, SyncHTTPClient
from .resources import (
    AsyncAutomationsResource,
    AsyncDomainsResource,
    AsyncInboundMessagesResource,
    AsyncMessagesResource,
    AsyncSendResource,
    AsyncSuppressionsResource,
    AsyncTemplatesResource,
    AsyncUsageResource,
    AsyncWebhooksResource,
    AutomationsResource,
    DomainsResource,
    InboundMessagesResource,
    MessagesResource,
    SendResource,
    SuppressionsResource,
    TemplatesResource,
    UsageResource,
    WebhooksResource,
)


def _config(
    api_key: str,
    base_url: str,
    timeout: float,
    max_response_bytes: int,
    max_raw_response_bytes: int,
    max_retries: int,
    base_delay: float,
    max_delay: float,
) -> ClientConfig:
    return make_config(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_response_bytes=max_response_bytes,
        max_raw_response_bytes=max_raw_response_bytes,
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )


class ViaPost:
    """Synchronous ViaPost API client."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_raw_response_bytes: int = DEFAULT_MAX_RAW_RESPONSE_BYTES,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = _config(
            api_key,
            base_url,
            timeout,
            max_response_bytes,
            max_raw_response_bytes,
            max_retries,
            base_delay,
            max_delay,
        )
        self._client = httpx.Client(transport=transport, timeout=timeout)
        self._http = SyncHTTPClient(self._config, self._client)
        self.messages = MessagesResource(self._http)
        self.inbound_messages = InboundMessagesResource(self._http)
        self.send = SendResource(self._http)
        self.suppressions = SuppressionsResource(self._http)
        self.domains = DomainsResource(self._http)
        self.templates = TemplatesResource(self._http)
        self.webhooks = WebhooksResource(self._http)
        self.automations = AutomationsResource(self._http)
        self.usage = UsageResource(self._http)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ViaPost:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncViaPost:
    """Asynchronous ViaPost API client."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_raw_response_bytes: int = DEFAULT_MAX_RAW_RESPONSE_BYTES,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = _config(
            api_key,
            base_url,
            timeout,
            max_response_bytes,
            max_raw_response_bytes,
            max_retries,
            base_delay,
            max_delay,
        )
        self._client = httpx.AsyncClient(transport=transport, timeout=timeout)
        self._http = AsyncHTTPClient(self._config, self._client)
        self.messages = AsyncMessagesResource(self._http)
        self.inbound_messages = AsyncInboundMessagesResource(self._http)
        self.send = AsyncSendResource(self._http)
        self.suppressions = AsyncSuppressionsResource(self._http)
        self.domains = AsyncDomainsResource(self._http)
        self.templates = AsyncTemplatesResource(self._http)
        self.webhooks = AsyncWebhooksResource(self._http)
        self.automations = AsyncAutomationsResource(self._http)
        self.usage = AsyncUsageResource(self._http)

    @property
    def base_url(self) -> str:
        return self._config.base_url

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncViaPost:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
