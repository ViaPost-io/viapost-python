"""Compare the vendored OpenAPI document with the published contract semantically."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

CONTRACT_URL = "https://docs.viapost.io/openapi/public.yaml"
LOCAL_CONTRACT = Path(__file__).parents[1] / "src" / "viapost" / "openapi.yaml"


def load_yaml(source: str) -> object:
    document = yaml.safe_load(source)
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3.1"):
        raise ValueError("expected a valid OpenAPI 3.1 document")
    return document


def main() -> int:
    local = load_yaml(LOCAL_CONTRACT.read_text(encoding="utf-8"))
    request = Request(CONTRACT_URL, headers={"User-Agent": "viapost-python-contract-check/0.1"})
    with urlopen(request, timeout=15) as response:
        remote = load_yaml(response.read().decode("utf-8"))
    if local != remote:
        print(f"Vendored OpenAPI differs semantically from {CONTRACT_URL}.", file=sys.stderr)
        return 1
    print("Vendored OpenAPI is semantically synchronized with the published contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
