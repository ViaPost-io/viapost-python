"""Explicit, redaction-safe containers for one-time webhook secrets."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from .types import WebhookEndpoint

_REDACTED: Final = "<redacted>"
_SENSITIVE_FIELDS: Final = frozenset(
    {"api_key", "authorization", "credential", "key", "password", "secret", "token"}
)


def _redact(value: object, secret: str | None = None, *, field: str | None = None) -> object:
    normalized = "" if field is None else field.lower().replace("-", "_")
    if normalized in _SENSITIVE_FIELDS or normalized.endswith(("_secret", "_token", "_password")):
        return _REDACTED
    if isinstance(value, str):
        return value.replace(secret, _REDACTED) if secret else value
    if isinstance(value, Mapping):
        return {str(key): _redact(item, secret, field=str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item, secret) for item in value)
    return value


def _safe_endpoint(endpoint: WebhookEndpoint, secret: str | None) -> WebhookEndpoint:
    return cast(WebhookEndpoint, _redact(endpoint, secret))


class CreateWebhookResponse:
    """Webhook creation result.

    ``secret`` is intentionally available only through an explicit property.  String
    rendering and :meth:`to_dict` never reveal it.
    """

    __slots__ = ("_endpoint", "_secret")

    def __init__(self, endpoint: WebhookEndpoint, secret: str) -> None:
        self._endpoint = endpoint
        self._secret = secret

    @property
    def endpoint(self) -> WebhookEndpoint:
        return self._endpoint

    @property
    def secret(self) -> str:
        """Return the one-time secret. Avoid logging or persisting this value."""

        return self._secret

    def to_dict(self) -> dict[str, object]:
        """Return a representation safe for ordinary logs/serialization."""

        return {"endpoint": _safe_endpoint(self._endpoint, self._secret), "secret": _REDACTED}

    def __repr__(self) -> str:
        endpoint = _safe_endpoint(self._endpoint, self._secret)
        return f"CreateWebhookResponse(endpoint={endpoint!r}, secret={_REDACTED!r})"

    __str__ = __repr__

    def __getstate__(self) -> Mapping[str, object]:
        return self.to_dict()

    def __reduce__(self) -> tuple[type[CreateWebhookResponse], tuple[WebhookEndpoint, str]]:
        return (type(self), (_safe_endpoint(self._endpoint, self._secret), _REDACTED))


class RotateWebhookSecretResponse:
    """Webhook secret rotation result with redaction-safe rendering."""

    __slots__ = ("_endpoint", "_rotated_at", "_secret")

    def __init__(
        self, endpoint: WebhookEndpoint, rotated_at: str, secret: str | None = None
    ) -> None:
        self._endpoint = endpoint
        self._rotated_at = rotated_at
        self._secret = secret

    @property
    def endpoint(self) -> WebhookEndpoint:
        return self._endpoint

    @property
    def rotated_at(self) -> str:
        return self._rotated_at

    @property
    def secret(self) -> str | None:
        """Return the one-time secret when the server supplied one."""

        return self._secret

    def to_dict(self) -> dict[str, object]:
        return {
            "endpoint": _safe_endpoint(self._endpoint, self._secret),
            "rotated_at": self._rotated_at,
            "secret": _REDACTED if self._secret is not None else None,
        }

    def __repr__(self) -> str:
        endpoint = _safe_endpoint(self._endpoint, self._secret)
        return (
            "RotateWebhookSecretResponse("
            f"endpoint={endpoint!r}, rotated_at={self._rotated_at!r}, "
            f"secret={_REDACTED!r})"
        )

    __str__ = __repr__

    def __getstate__(self) -> Mapping[str, object]:
        return self.to_dict()

    def __reduce__(
        self,
    ) -> tuple[type[RotateWebhookSecretResponse], tuple[WebhookEndpoint, str, str | None]]:
        safe_secret = _REDACTED if self._secret is not None else None
        endpoint = _safe_endpoint(self._endpoint, self._secret)
        return (type(self), (endpoint, self._rotated_at, safe_secret))
