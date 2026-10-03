"""Access to the exact OpenAPI contract snapshot used by this SDK release."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

OPENAPI_SOURCE_URL = "https://docs.viapost.io/openapi/public.yaml"
OPENAPI_SHA256 = "d42e0c5d732780b743aead543be32d6b474631dec4fd0c1c8838e1416216bc4e"


def openapi_path() -> Path:
    """Return the vendored OpenAPI snapshot path for filesystem installations."""

    return Path(str(files("viapost").joinpath("openapi.yaml")))


def read_openapi() -> str:
    """Read the vendored OpenAPI snapshot as UTF-8 text."""

    return files("viapost").joinpath("openapi.yaml").read_text(encoding="utf-8")
