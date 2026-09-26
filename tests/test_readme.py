"""Keep release-install documentation aligned with published releases."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_release_artifact_urls_match_latest_changelog_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    version = re.search(r'^version = "(?P<version>[^\"]+)"$', project, re.MULTILINE)
    published = re.search(r"^## \[(?P<version>\d+\.\d+\.\d+)\] - ", changelog, re.MULTILINE)

    assert version is not None
    assert published is not None
    release_version = published["version"]
    # The source may already target the next version; README must not point to
    # an artifact for that unpublished version.
    assert tuple(map(int, release_version.split("."))) <= tuple(
        map(int, version["version"].split("."))
    )
    wheel_url = (
        "https://github.com/ViaPost-io/viapost-python/releases/download/"
        f"v{release_version}/viapost-{release_version}-py3-none-any.whl"
    )

    assert f"pip install {wheel_url}" in readme
    assert f"viapost-{release_version}.tar.gz" in readme
    assert set(re.findall(r"viapost-(\d+\.\d+\.\d+)(?:-py3-none-any\.whl|\.tar\.gz)", readme)) == {
        release_version
    }
