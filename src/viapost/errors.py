"""Typed ViaPost SDK exceptions."""

from __future__ import annotations

from collections.abc import Mapping


class ViaPostError(Exception):
    """Base class for all ViaPost SDK exceptions."""


class ViaPostAPIError(ViaPostError):
    """A non-successful response returned by the ViaPost API."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        method: str,
        url: str,
        body: object,
        request_id: str | None,
        headers: Mapping[str, str],
    ) -> None:
        super().__init__(message)
        self.status = status
        self.method = method
        self.url = url
        self.body = body
        self.request_id = request_id
        self.headers = headers


class ViaPostTimeoutError(ViaPostError):
    """A request exceeded its configured timeout."""

    def __init__(self, timeout: float) -> None:
        super().__init__(f"ViaPost request timed out after {timeout:g}s")
        self.timeout = timeout


class ViaPostConnectionError(ViaPostError):
    """A request could not connect to the ViaPost API."""

    def __init__(self) -> None:
        super().__init__("Unable to connect to the ViaPost API")


class ViaPostResponseTooLargeError(ViaPostError):
    """A response exceeded the configured decoded-body limit."""

    def __init__(self, max_response_bytes: int) -> None:
        super().__init__(f"ViaPost response exceeded the {max_response_bytes}-byte limit")
        self.max_response_bytes = max_response_bytes
