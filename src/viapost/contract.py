"""Access to the exact OpenAPI contract snapshot used by this SDK release."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

OPENAPI_SHA256 = "d1f223342ad1ca326ba716af6e508c78594e1b108958cce2ec4a1efd31a9773a"


def openapi_path() -> Path:
    """Return the vendored OpenAPI snapshot path for filesystem installations."""

    return Path(str(files("viapost").joinpath("openapi.yaml")))


def read_openapi() -> str:
    """Read the vendored OpenAPI snapshot as UTF-8 text."""

    return files("viapost").joinpath("openapi.yaml").read_text(encoding="utf-8")
