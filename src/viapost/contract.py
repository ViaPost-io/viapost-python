"""Access to the exact OpenAPI contract snapshot used by this SDK release."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

OPENAPI_SOURCE_URL = "https://docs.viapost.io/openapi/public.yaml"
OPENAPI_SHA256 = "14b629c986087e273923791af3b54792426cf70c943c176ccd41285e7c20aad0"


def openapi_path() -> Path:
    """Return the vendored OpenAPI snapshot path for filesystem installations."""

    return Path(str(files("viapost").joinpath("openapi.yaml")))


def read_openapi() -> str:
    """Read the vendored OpenAPI snapshot as UTF-8 text."""

    return files("viapost").joinpath("openapi.yaml").read_text(encoding="utf-8")
