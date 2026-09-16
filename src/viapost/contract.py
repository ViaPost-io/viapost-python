"""Access to the exact OpenAPI contract snapshot used by this SDK release."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

OPENAPI_SOURCE_URL = "https://docs.viapost.io/openapi/public.yaml"
OPENAPI_SHA256 = "f1b1fc0f198a2b0b36f0e893515dad191d6bb7d139fcf1e942c036bfa2f5169b"


def openapi_path() -> Path:
    """Return the vendored OpenAPI snapshot path for filesystem installations."""

    return Path(str(files("viapost").joinpath("openapi.yaml")))


def read_openapi() -> str:
    """Read the vendored OpenAPI snapshot as UTF-8 text."""

    return files("viapost").joinpath("openapi.yaml").read_text(encoding="utf-8")
