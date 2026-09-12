from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]


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


def test_release_toolchain_is_audited_and_pypi_runs_last() -> None:
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
        "attach-to-github-release",
        "attest-build-provenance",
    }

    release_lock = Path(".github/requirements/release.txt").read_text()
    assert "pip==26.2.1" in release_lock
    assert "pip==25.3" not in release_lock

    attach_step = next(
        step
        for step in jobs["attach-to-github-release"]["steps"]
        if step.get("name") == "Attach installable packages and checksums"
    )
    assert attach_step["env"]["GH_REPO"] == "${{ github.repository }}"


def test_release_build_requires_head_to_match_the_exact_tag() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["verify-and-build"]["steps"]
    exact_tag = next(
        step for step in steps if step.get("name") == "Require exact release tag commit on main"
    )

    assert "refs/tags/${RELEASE_TAG}:refs/tags/${RELEASE_TAG}" in exact_tag["run"]
    assert 'git rev-parse "refs/tags/${RELEASE_TAG}^{commit}"' in exact_tag["run"]
    assert "git merge-base --is-ancestor HEAD origin/main" in exact_tag["run"]
