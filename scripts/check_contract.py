"""Compare the vendored OpenAPI document with the published contract semantically."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import yaml  # type: ignore[import-untyped]

CONTRACT_URL = "https://docs.viapost.io/openapi/public.yaml"
LOCAL_CONTRACT = Path(__file__).parents[1] / "src" / "viapost" / "openapi.yaml"
ALLOWED_CONTRACT_HOSTS = frozenset({"docs.viapost.io"})
MAX_CONTRACT_BYTES = 2 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024


class _ReadableResponse(Protocol):
    headers: object

    def read(self, size: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    def __enter__(self) -> _ReadableResponse: ...

    def __exit__(self, *args: object) -> object: ...


class _Opener(Protocol):
    def open(self, request: Request, *, timeout: float) -> _ReadableResponse: ...


def validate_contract_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("contract source must use an approved HTTPS host") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_CONTRACT_HOSTS
        or _is_numeric_ipv4_alias(parsed.hostname or "")
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
        or port not in (None, 443)
    ):
        raise ValueError("contract source must use an approved HTTPS host")


def _is_numeric_ipv4_alias(hostname: str) -> bool:
    """Recognize legacy IPv4 spellings accepted by some HTTP stacks.

    These are deliberately rejected before allow-listing or redirect handling so a
    future host-list change cannot turn ``127.1`` or an integer/hex spelling into
    an SSRF bypass.
    """

    parts = hostname.lower().rstrip(".").split(".")
    if not 1 <= len(parts) <= 4 or any(not part for part in parts):
        return False
    values: list[int] = []
    for part in parts:
        base = 16 if part.startswith("0x") else 8 if len(part) > 1 and part.startswith("0") else 10
        digits = part[2:] if base == 16 else part
        if not digits:
            return False
        try:
            value = int(digits, base)
        except ValueError:
            return False
        if value < 0:
            return False
        values.append(value)
    if any(value > 255 for value in values[:-1]):
        return False
    return values[-1] <= (1 << (8 * (5 - len(values)))) - 1


class ApprovedHTTPSRedirectHandler(HTTPRedirectHandler):
    """Reject redirects before urllib sends credentials or bytes to another host."""

    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request | None:
        target = urljoin(req.full_url, newurl)
        validate_contract_url(target)
        return super().redirect_request(req, fp, code, msg, headers, target)  # type: ignore[arg-type]


def _content_length(headers: object) -> int | None:
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    raw = getter("content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _read_limited(response: _ReadableResponse) -> bytes:
    length = _content_length(response.headers)
    if length is not None and length > MAX_CONTRACT_BYTES:
        raise ValueError("published contract exceeds the size limit")
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = response.read(min(READ_CHUNK_BYTES, MAX_CONTRACT_BYTES - size + 1))
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_CONTRACT_BYTES:
            raise ValueError("published contract exceeds the size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_contract(source: str, *, opener: _Opener | None = None) -> str:
    validate_contract_url(source)
    active_opener = opener or cast(_Opener, build_opener(ApprovedHTTPSRedirectHandler()))
    request = Request(source, headers={"User-Agent": "viapost-python-contract-check/0.3.0"})
    with active_opener.open(request, timeout=15) as response:
        validate_contract_url(response.geturl())
        return _read_limited(response).decode("utf-8")


def load_yaml(source: str) -> object:
    document = yaml.safe_load(source)
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3.1"):
        raise ValueError("expected a valid OpenAPI 3.1 document")
    return document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=CONTRACT_URL, help="published OpenAPI URL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local = load_yaml(LOCAL_CONTRACT.read_text(encoding="utf-8"))
    remote = load_yaml(fetch_contract(args.source))
    if local != remote:
        print(f"Vendored OpenAPI differs semantically from {args.source}.", file=sys.stderr)
        return 1
    print("Vendored OpenAPI is semantically synchronized with the published contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
