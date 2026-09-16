"""HTTP transport shared by public resources."""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import cast

import httpx

from ._config import ClientConfig
from .errors import (
    ViaPostAPIError,
    ViaPostConnectionError,
    ViaPostResponseTooLargeError,
    ViaPostTimeoutError,
)


def _error_message(body: object, status: int) -> str:
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, str):
            return error
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
    return f"ViaPost API request failed with status {status}"


def _request_id(response: httpx.Response, body: object) -> str | None:
    header_id = response.headers.get("x-request-id") or response.headers.get("x-correlation-id")
    if isinstance(header_id, str) and header_id:
        return header_id
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        value = body["error"].get("request_id")
        return value if isinstance(value, str) and value else None
    return None


def _decode_bytes(status: int, content: bytes) -> object:
    if status in {204, 205, 304} or not content:
        return None
    text = content.decode("utf-8", errors="replace")
    try:
        return cast(object, json.loads(text))
    except ValueError:
        return text


def _check_content_length(response: httpx.Response, limit: int) -> None:
    content_encoding = response.headers.get("content-encoding", "identity").strip().lower()
    if content_encoding not in {"", "identity"}:
        return
    value = response.headers.get("content-length")
    if value is not None:
        try:
            if int(value) > limit:
                raise ViaPostResponseTooLargeError(limit)
        except ValueError:
            pass


def _read_limited(response: httpx.Response, limit: int) -> bytes:
    _check_content_length(response, limit)
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > limit:
            raise ViaPostResponseTooLargeError(limit)
        chunks.append(chunk)
    return b"".join(chunks)


async def _aread_limited(response: httpx.Response, limit: int) -> bytes:
    _check_content_length(response, limit)
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > limit:
            raise ViaPostResponseTooLargeError(limit)
        chunks.append(chunk)
    return b"".join(chunks)


_SENSITIVE_FIELDS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "set_cookie",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "client_secret",
        "credential",
        "credentials",
        "key",
        "password",
        "private_key",
        "session",
        "signing_key",
    }
)


def _redact(value: object, api_key: str, *, field: str | None = None) -> object:
    sensitive_values = _extract_sensitive_values(value)
    if api_key:
        sensitive_values.add(api_key)
    return _redact_values(value, sensitive_values, field=field)


def _is_sensitive_field(field: str | None) -> bool:
    normalized = "" if field is None else field.lower().replace("-", "_")
    return normalized in _SENSITIVE_FIELDS or any(
        marker in normalized
        for marker in ("secret", "token", "password", "api_key", "auth", "cookie")
    )


def _extract_sensitive_values(value: object, *, field: str | None = None) -> set[str]:
    if _is_sensitive_field(field):
        if isinstance(value, str) and value:
            return {value}
        if isinstance(value, Mapping):
            return {
                item
                for nested in value.values()
                for item in _extract_sensitive_values(nested, field=field)
            }
        if isinstance(value, (list, tuple)):
            return {
                item
                for nested in value
                for item in _extract_sensitive_values(nested, field=field)
            }
        return set()
    if isinstance(value, Mapping):
        return {
            item
            for key, nested in value.items()
            for item in _extract_sensitive_values(nested, field=str(key))
        }
    if isinstance(value, (list, tuple)):
        return {item for nested in value for item in _extract_sensitive_values(nested)}
    return set()


def _redact_values(
    value: object, sensitive_values: set[str], *, field: str | None = None
) -> object:
    if _is_sensitive_field(field):
        return "<redacted>"
    if isinstance(value, str):
        for secret in sensitive_values:
            value = value.replace(secret, "<redacted>")
        return value
    if isinstance(value, Mapping):
        return {
            _redact_values(str(key), sensitive_values): _redact_values(
                item, sensitive_values, field=str(key)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_values(item, sensitive_values) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_values(item, sensitive_values) for item in value)
    return value


def _raise_api_error(response: httpx.Response, body: object, api_key: str) -> None:
    if response.is_success:
        return
    request = response.request
    safe_body = _redact(body, api_key)
    safe_headers = cast(dict[str, str], _redact(dict(response.headers), api_key))
    raise ViaPostAPIError(
        _error_message(safe_body, response.status_code),
        status=response.status_code,
        method=request.method,
        url=str(request.url),
        body=safe_body,
        request_id=cast(str | None, _redact(_request_id(response, body), api_key)),
        headers=safe_headers,
    )


def _is_retryable(method: str, status: int) -> bool:
    return method.upper() in {"GET", "HEAD"} and (status == 429 or 500 <= status <= 599)


def _retry_delay(response: httpx.Response, attempt: int, config: ClientConfig) -> float:
    value = response.headers.get("retry-after")
    if value:
        try:
            seconds = float(value)
            if math.isfinite(seconds) and seconds >= 0:
                return min(seconds, config.max_delay)
        except ValueError:
            pass
        try:
            target = parsedate_to_datetime(value)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            seconds = (target - datetime.now(timezone.utc)).total_seconds()
            if seconds > 0:
                return min(seconds, config.max_delay)
        except (TypeError, ValueError, OverflowError):
            pass
    return float(min(config.base_delay * (2**attempt), config.max_delay))


def _effective_timeout(config: ClientConfig, override: float | None) -> float:
    value = config.timeout if override is None else override
    if not math.isfinite(value) or value <= 0:
        raise ValueError("timeout must be positive")
    return value


def _query_params(query: Mapping[str, object] | None) -> httpx.QueryParams:
    items: list[tuple[str, str | int | float | bool | None]] = []
    for key, raw in (query or {}).items():
        if raw is None:
            continue
        values = raw if isinstance(raw, Sequence) and not isinstance(raw, str) else [raw]
        for value in values:
            items.append((key, str(value).lower() if isinstance(value, bool) else str(value)))
    return httpx.QueryParams(items)


class SyncHTTPClient:
    def __init__(self, config: ClientConfig, client: httpx.Client) -> None:
        self.config = config
        self.client = client

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, object] | None = None,
        body: object | None = None,
        content: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
        accept: str = "application/json",
        content_type: str | None = None,
        raw_response: bool = False,
        timeout: float | None = None,
    ) -> object:
        if body is not None and content is not None:
            raise ValueError("body and content cannot be provided together")
        request_headers = httpx.Headers(headers)
        request_headers["Authorization"] = f"Bearer {self.config.api_key}"
        request_headers["Accept"] = accept
        request_headers["User-Agent"] = "viapost-python/0.2.0"
        if content_type is not None:
            request_headers["Content-Type"] = content_type
        effective_timeout = _effective_timeout(self.config, timeout)
        json_body: object | None = body
        attempt = 0
        while True:
            transport_error: ViaPostTimeoutError | ViaPostConnectionError | None = None
            try:
                with self.client.stream(
                    method,
                    f"{self.config.base_url}/{path.lstrip('/')}",
                    params=_query_params(query),
                    headers=request_headers,
                    timeout=effective_timeout,
                    json=json_body,
                    content=content,
                    follow_redirects=False,
                ) as response:
                    limit = (
                        self.config.max_raw_response_bytes
                        if raw_response and response.is_success
                        else self.config.max_response_bytes
                    )
                    response_bytes = _read_limited(response, limit)
                    decoded = (
                        response_bytes
                        if raw_response and response.is_success
                        else _decode_bytes(response.status_code, response_bytes)
                    )
                    if (
                        _is_retryable(method, response.status_code)
                        and attempt < self.config.max_retries
                    ):
                        time.sleep(_retry_delay(response, attempt, self.config))
                        attempt += 1
                        continue
                    _raise_api_error(response, decoded, self.config.api_key)
                    return decoded
            except httpx.TimeoutException:
                transport_error = ViaPostTimeoutError(effective_timeout)
            except httpx.RequestError:
                transport_error = ViaPostConnectionError()
            if transport_error is not None:
                raise transport_error


class AsyncHTTPClient:
    def __init__(self, config: ClientConfig, client: httpx.AsyncClient) -> None:
        self.config = config
        self.client = client

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, object] | None = None,
        body: object | None = None,
        content: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
        accept: str = "application/json",
        content_type: str | None = None,
        raw_response: bool = False,
        timeout: float | None = None,
    ) -> object:
        if body is not None and content is not None:
            raise ValueError("body and content cannot be provided together")
        request_headers = httpx.Headers(headers)
        request_headers["Authorization"] = f"Bearer {self.config.api_key}"
        request_headers["Accept"] = accept
        request_headers["User-Agent"] = "viapost-python/0.2.0"
        if content_type is not None:
            request_headers["Content-Type"] = content_type
        effective_timeout = _effective_timeout(self.config, timeout)
        json_body: object | None = body
        attempt = 0
        while True:
            transport_error: ViaPostTimeoutError | ViaPostConnectionError | None = None
            try:
                async with self.client.stream(
                    method,
                    f"{self.config.base_url}/{path.lstrip('/')}",
                    params=_query_params(query),
                    headers=request_headers,
                    timeout=effective_timeout,
                    json=json_body,
                    content=content,
                    follow_redirects=False,
                ) as response:
                    limit = (
                        self.config.max_raw_response_bytes
                        if raw_response and response.is_success
                        else self.config.max_response_bytes
                    )
                    response_bytes = await _aread_limited(response, limit)
                    decoded = (
                        response_bytes
                        if raw_response and response.is_success
                        else _decode_bytes(response.status_code, response_bytes)
                    )
                    if (
                        _is_retryable(method, response.status_code)
                        and attempt < self.config.max_retries
                    ):
                        await asyncio.sleep(_retry_delay(response, attempt, self.config))
                        attempt += 1
                        continue
                    _raise_api_error(response, decoded, self.config.api_key)
                    return decoded
            except httpx.TimeoutException:
                transport_error = ViaPostTimeoutError(effective_timeout)
            except httpx.RequestError:
                transport_error = ViaPostConnectionError()
            if transport_error is not None:
                raise transport_error
