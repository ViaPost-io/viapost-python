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


def _raise_api_error(response: httpx.Response, body: object) -> None:
    if response.is_success:
        return
    request = response.request
    raise ViaPostAPIError(
        _error_message(body, response.status_code),
        status=response.status_code,
        method=request.method,
        url=str(request.url),
        body=body,
        request_id=_request_id(response, body),
        headers=response.headers,
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
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> object:
        request_headers = httpx.Headers(headers)
        request_headers["Authorization"] = f"Bearer {self.config.api_key}"
        request_headers["Accept"] = "application/json"
        request_headers["User-Agent"] = "viapost-python/0.1.3"
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
                    follow_redirects=False,
                ) as response:
                    decoded = _decode_bytes(
                        response.status_code,
                        _read_limited(response, self.config.max_response_bytes),
                    )
                    if (
                        _is_retryable(method, response.status_code)
                        and attempt < self.config.max_retries
                    ):
                        time.sleep(_retry_delay(response, attempt, self.config))
                        attempt += 1
                        continue
                    _raise_api_error(response, decoded)
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
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> object:
        request_headers = httpx.Headers(headers)
        request_headers["Authorization"] = f"Bearer {self.config.api_key}"
        request_headers["Accept"] = "application/json"
        request_headers["User-Agent"] = "viapost-python/0.1.3"
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
                    follow_redirects=False,
                ) as response:
                    decoded = _decode_bytes(
                        response.status_code,
                        await _aread_limited(response, self.config.max_response_bytes),
                    )
                    if (
                        _is_retryable(method, response.status_code)
                        and attempt < self.config.max_retries
                    ):
                        await asyncio.sleep(_retry_delay(response, attempt, self.config))
                        attempt += 1
                        continue
                    _raise_api_error(response, decoded)
                    return decoded
            except httpx.TimeoutException:
                transport_error = ViaPostTimeoutError(effective_timeout)
            except httpx.RequestError:
                transport_error = ViaPostConnectionError()
            if transport_error is not None:
                raise transport_error
