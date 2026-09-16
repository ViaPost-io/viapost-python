from __future__ import annotations

import pickle

import pytest

from viapost import AsyncViaPost, ViaPost
from viapost._config import make_config


def test_constructor_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError, match="api_key must be a non-empty string"):
        ViaPost(api_key="  ")


@pytest.mark.parametrize("client_class", [ViaPost, AsyncViaPost])
@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"base_url": "http://api.example.com"}, "HTTPS except for loopback"),
        ({"base_url": "ftp://example.com"}, "absolute HTTP\\(S\\) URL"),
        ({"base_url": "https://user:pass@example.com"}, "must not contain credentials"),
        ({"timeout": 0}, "timeout must be positive"),
        ({"max_response_bytes": 0}, "max_response_bytes must be positive"),
        ({"max_response_bytes": 8 * 1024 * 1024 + 1}, "at most 8 MiB"),
        ({"max_raw_response_bytes": 0}, "max_raw_response_bytes must be positive"),
        ({"max_raw_response_bytes": 64 * 1024 * 1024 + 1}, "at most 64 MiB"),
        ({"max_retries": -1}, "max_retries must be non-negative"),
    ],
)
def test_constructor_rejects_unsafe_or_invalid_options(
    client_class: type[ViaPost] | type[AsyncViaPost], kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        client_class(api_key="vp_test", **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:15080", "http://api.localhost:15080", "http://127.0.0.1", "http://[::1]"],
)
def test_constructor_allows_plain_http_only_for_loopback(base_url: str) -> None:
    with ViaPost(api_key="vp_test", base_url=base_url) as client:
        assert client.base_url.startswith("http://")


@pytest.mark.parametrize("api_key", ["line\nbreak", "tab\tkey", "café", "contains space"])
def test_constructor_rejects_api_keys_that_are_not_visible_ascii(api_key: str) -> None:
    with pytest.raises(ValueError, match="visible ASCII"):
        ViaPost(api_key=api_key)


def test_client_config_never_renders_or_pickles_the_api_key() -> None:
    api_key = "vp_live_config-do-not-disclose"
    config = make_config(
        api_key=api_key,
        base_url="https://api.viapost.io",
        timeout=60,
        max_response_bytes=1024,
        max_raw_response_bytes=2048,
        max_retries=2,
        base_delay=0.25,
        max_delay=30,
    )

    assert api_key not in repr(config)
    serialized = pickle.dumps(config)
    assert api_key.encode() not in serialized
    restored = pickle.loads(serialized)
    assert restored.api_key == "<redacted>"
    assert restored.base_url == config.base_url
