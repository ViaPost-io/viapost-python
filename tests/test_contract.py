from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from viapost import (
    DeliverabilityMetrics,
    DeliverabilityProviderMetrics,
    DeliverabilityRejections,
    MetricsResponse,
    __version__,
)
from viapost.contract import OPENAPI_SHA256, OPENAPI_SOURCE_URL, read_openapi
from viapost.resources import AsyncAutomationsResource, AutomationsResource


def test_vendored_openapi_snapshot_is_verifiable() -> None:
    source = read_openapi()
    assert source.startswith("openapi: 3.1.1\n")
    assert hashlib.sha256(source.encode()).hexdigest() == OPENAPI_SHA256


def test_public_version_matches_project_metadata() -> None:
    project = Path("pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', project, re.MULTILINE)

    assert version is not None
    assert __version__ == version.group(1) == "0.4.0"


def test_contract_release_bumps_the_previous_public_version() -> None:
    previous_release = (0, 3, 0)
    current_release = tuple(int(part) for part in __version__.split("."))

    assert current_release == (0, 4, 0)
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


def test_vendored_openapi_includes_the_r04_deliverability_contract() -> None:
    document = yaml.safe_load(read_openapi())
    event_send = document["paths"]["/v1/events/send"]["post"]
    metrics = document["components"]["schemas"]["MetricsResponse"]

    assert "Idempotency-Key" in {
        parameter["name"] for parameter in event_send["parameters"] if "name" in parameter
    }
    assert "deliverability" in metrics["required"]
    assert metrics["properties"]["deliverability"] == {
        "$ref": "#/components/schemas/DeliverabilityMetrics"
    }


def test_session_only_onboarding_recipe_is_documented_but_not_exposed_by_api_key_sdk() -> None:
    document = yaml.safe_load(read_openapi())
    recipe = document["paths"]["/v1/automations/{id}/recipes/saas-onboarding"]["patch"]

    assert recipe["security"] == [{"sessionCookie": []}]
    assert {parameter.get("name") for parameter in recipe["parameters"]} >= {
        "id",
        "X-ViaPost-Expected-Tenant-ID",
    }
    assert any(
        parameter.get("$ref") == "#/components/parameters/RequiredCsrfHeader"
        for parameter in recipe["parameters"]
    )
    assert document["components"]["parameters"]["RequiredCsrfHeader"]["name"] == "X-ViaPost-Csrf"
    request = document["components"]["schemas"]["MaterializeSaasOnboardingRecipeRequest"]
    assert set(request["required"]) == {"event_id", "template_id", "sender_domain_id"}
    assert recipe["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Automation"
    }
    assert not hasattr(AutomationsResource, "materialize_saas_onboarding_recipe")
    assert not hasattr(AsyncAutomationsResource, "materialize_saas_onboarding_recipe")


def test_generated_metrics_types_expose_r04_deliverability_without_breaking_old_consumers() -> None:
    assert MetricsResponse.__required_keys__ == {
        "since",
        "until",
        "current",
        "previous",
        "timeseries",
        "by_domain",
    }
    assert MetricsResponse.__optional_keys__ == {"deliverability"}
    assert DeliverabilityMetrics.__required_keys__ == {
        "providers",
        "rejections",
        "previous_rejections",
        "problem_domains",
        "volume",
    }
    assert DeliverabilityProviderMetrics.__required_keys__ == {"provider", "total", "delivered"}
    assert DeliverabilityRejections.__required_keys__ == {
        "soft_bounce",
        "hard_bounce",
        "policy_block",
        "nonexistent_domain",
        "other",
    }
