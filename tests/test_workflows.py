from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]


def test_scheduled_contract_check_uses_the_public_contract_source() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/contract-drift.yml").read_text())
    steps = workflow["jobs"]["check"]["steps"]
    script = next(step["run"] for step in steps if "check_contract.py" in step.get("run", ""))

    assert "https://docs.viapost.io/openapi/public.yaml" in script
    assert "raw.githubusercontent.com" not in script


def test_release_artifact_is_sealed_before_isolated_consumer_install() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["verify-and-build"]["steps"]
    named_steps = {step.get("name"): index for index, step in enumerate(steps)}

    checksum = named_steps["Create checksums"]
    protect = named_steps["Make built distributions read-only"]
    consumer = named_steps["Test wheel in an isolated consumer environment"]
    upload = next(
        index
        for index, step in enumerate(steps)
        if step.get("with", {}).get("name") == "python-distributions"
    )

    assert checksum < protect < upload < consumer
    assert "chmod -R a-w dist checksums" in steps[protect]["run"]
    consumer_script = steps[consumer]["run"]
    assert consumer_script.index("cp dist/*.whl") < consumer_script.index("--require-hashes")
    assert "--require-hashes -" in consumer_script
    assert ".github/requirements/runtime.txt" in consumer_script
    assert "pip install --no-deps" in consumer_script
    assert "/tmp/viapost-consumer/artifacts/*.whl" in consumer_script
    assert "sha256sum -c" in consumer_script
    assert "pip install dist/*.whl" not in consumer_script


def test_release_toolchain_is_audited_and_publish_order_is_fail_closed() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
    jobs = workflow["jobs"]
    steps = jobs["verify-and-build"]["steps"]
    named_steps = {step.get("name"): index for index, step in enumerate(steps)}

    audit = named_steps["Audit hash-locked release toolchain"]
    build = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "python -m build --no-isolation"
    )
    assert audit < build
    assert steps[audit]["run"] == (
        "pip-audit --require-hashes --requirement .github/requirements/release.txt"
    )
    assert set(jobs["publish-to-pypi"]["needs"]) == {
        "verify-and-build",
        "attest-build-provenance",
        "publish-github-release",
    }
    assert jobs["publish-github-release"]["needs"] == [
        "verify-and-build",
        "attest-build-provenance",
    ]
    assert jobs["publish-to-pypi"]["environment"] == "pypi"

    release_lock = Path(".github/requirements/release.txt").read_text()
    assert "pip==26.2.1" in release_lock
    assert "pip==25.3" not in release_lock

    attach_step = next(
        step
        for step in jobs["publish-github-release"]["steps"]
        if step.get("name") == "Recover or publish the verified draft release"
    )
    assert attach_step["env"]["GH_REPO"] == "${{ github.repository }}"
    assert "--clobber" not in Path(".github/workflows/release.yml").read_text()
    assert "--clobber" not in Path("scripts/publish_release.py").read_text()


def test_release_is_driven_by_tag_or_manual_dispatch_not_release_publication() -> None:
    source = Path(".github/workflows/release.yml").read_text()
    assert "push:" in source and "tags:" in source
    assert "workflow_dispatch:" in source
    assert "\n  release:\n" not in source
    assert "scripts/publish_release.py" in source


def test_release_build_requires_head_to_match_the_exact_tag() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["verify-and-build"]["steps"]
    exact_tag = next(
        step for step in steps if step.get("name") == "Require exact release tag commit on main"
    )

    assert "refs/tags/${RELEASE_TAG}:refs/tags/${RELEASE_TAG}" in exact_tag["run"]
    assert 'git rev-parse "refs/tags/${RELEASE_TAG}^{commit}"' in exact_tag["run"]
    assert "git merge-base --is-ancestor HEAD origin/main" in exact_tag["run"]
