"""Client configuration validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit

DEFAULT_BASE_URL = "https://api.viapost.io"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY = 0.25
DEFAULT_MAX_DELAY = 30.0


@dataclass(frozen=True, slots=True)
class ClientConfig:
    api_key: str
    base_url: str
    timeout: float
    max_response_bytes: int
    max_retries: int
    base_delay: float
    max_delay: float


def make_config(
    *,
    api_key: str,
    base_url: str,
    timeout: float,
    max_response_bytes: int,
    max_retries: int,
    base_delay: float,
    max_delay: float,
) -> ClientConfig:
    if not isinstance(api_key, str):
        raise ValueError("api_key must be a non-empty string")
    normalized_key = api_key.strip()
    if not normalized_key:
        raise ValueError("api_key must be a non-empty string")
    if any(ord(char) < 0x21 or ord(char) > 0x7E for char in normalized_key):
        raise ValueError("api_key must contain only visible ASCII characters")
    if (
        not isinstance(timeout, int | float)
        or isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be positive")
    if (
        not isinstance(max_response_bytes, int)
        or isinstance(max_response_bytes, bool)
        or max_response_bytes <= 0
    ):
        raise ValueError("max_response_bytes must be positive")
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    if (
        not isinstance(base_delay, int | float)
        or isinstance(base_delay, bool)
        or not math.isfinite(base_delay)
        or base_delay < 0
        or not isinstance(max_delay, int | float)
        or isinstance(max_delay, bool)
        or not math.isfinite(max_delay)
        or max_delay < 0
    ):
        raise ValueError("retry delays must be non-negative")
    return ClientConfig(
        normalized_key,
        normalize_base_url(base_url),
        float(timeout),
        max_response_bytes,
        max_retries,
        float(base_delay),
        float(max_delay),
    )


def normalize_base_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("base_url must be an absolute HTTP(S) URL") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or (port is None and not parsed.netloc)
    ):
        raise ValueError("base_url must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("base_url must not contain credentials")
    if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
        raise ValueError("base_url must use HTTPS except for loopback development hosts")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _is_loopback(hostname: str) -> bool:
    name = hostname.lower()
    if name == "localhost" or name.endswith(".localhost"):
        return True
    try:
        return ip_address(name).is_loopback
    except ValueError:
        return False
