from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from viapost import __version__
from viapost.contract import OPENAPI_SHA256, OPENAPI_SOURCE_URL, read_openapi


def test_vendored_openapi_snapshot_is_verifiable() -> None:
    source = read_openapi()
    assert source.startswith("openapi: 3.1.1\n")
    assert hashlib.sha256(source.encode()).hexdigest() == OPENAPI_SHA256


def test_public_version_matches_project_metadata() -> None:
    project = Path("pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', project, re.MULTILINE)

    assert version is not None
    assert __version__ == version.group(1) == "0.3.0"


def test_contract_release_bumps_the_previous_public_version() -> None:
    previous_release = (0, 2, 0)
    current_release = tuple(int(part) for part in __version__.split("."))

    assert current_release == (0, 3, 0)
    assert current_release > previous_release


def test_vendored_openapi_contains_the_current_authenticated_surface() -> None:
    document = yaml.safe_load(read_openapi())

    assert OPENAPI_SOURCE_URL == "https://docs.viapost.io/openapi/public.yaml"
    assert {
        "/v1/messages/{id}/raw",
        "/v1/inbound-messages/{id}/raw",
        "/v1/suppressions",
        "/v1/suppressions/import",
        "/v1/suppressions/export",
        "/v1/webhooks/{id}/deliveries",
        "/v1/webhooks/{id}/secret/rotate",
        "/v1/contacts/import",
        "/v1/domains/{domain_id}/tracking-domains",
        "/v1/segments",
        "/v1/segments/preview",
    } <= document["paths"].keys()
