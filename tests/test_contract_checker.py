from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import cast
from urllib.request import Request

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from scripts import check_contract


class _Response(io.BytesIO):
    def __init__(self, body: bytes, url: str, *, content_length: str | None = None) -> None:
        super().__init__(body)
        self._url = url
        self.headers = {} if content_length is None else {"content-length": content_length}

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class _Opener:
    def __init__(self, response: _Response) -> None:
        self.response = response

    def open(self, request: Request, *, timeout: float) -> _Response:
        return self.response


@pytest.mark.parametrize(
    "url",
    [
        "http://docs.viapost.io/openapi/public.yaml",
        "https://evil.example/openapi.yaml",
        "https://user@docs.viapost.io/openapi/public.yaml",
        "https://docs.viapost.io/openapi/public.yaml#fragment",
        "https://127.1/openapi/public.yaml",
        "https://2130706433/openapi/public.yaml",
        "https://0x7f000001/openapi/public.yaml",
    ],
)
def test_contract_source_requires_https_allowlisted_host(url: str) -> None:
    with pytest.raises(ValueError, match="approved HTTPS"):
        check_contract.validate_contract_url(url)


@pytest.mark.parametrize("hostname", ["127.1", "2130706433", "0x7f000001"])
def test_numeric_ipv4_aliases_are_detected_before_host_allowlisting(hostname: str) -> None:
    assert check_contract._is_numeric_ipv4_alias(hostname)


def test_contract_fetch_rejects_unapproved_final_redirect_host() -> None:
    opener = _Opener(_Response(b"openapi: 3.1.0", "https://evil.example/openapi.yaml"))
    with pytest.raises(ValueError, match="approved HTTPS"):
        check_contract.fetch_contract(
            check_contract.CONTRACT_URL, opener=cast(check_contract._Opener, opener)
        )


def test_contract_fetch_reads_incrementally_with_a_hard_limit() -> None:
    body = b"x" * (check_contract.MAX_CONTRACT_BYTES + 1)
    opener = _Opener(_Response(body, check_contract.CONTRACT_URL))
    with pytest.raises(ValueError, match="size limit"):
        check_contract.fetch_contract(
            check_contract.CONTRACT_URL, opener=cast(check_contract._Opener, opener)
        )

    oversized = _Opener(_Response(b"", check_contract.CONTRACT_URL, content_length=str(len(body))))
    with pytest.raises(ValueError, match="size limit"):
        check_contract.fetch_contract(
            check_contract.CONTRACT_URL, opener=cast(check_contract._Opener, oversized)
        )
