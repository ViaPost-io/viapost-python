"""Fail closed when README install instructions do not name published assets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LATEST_RELEASE_URL = "https://api.github.com/repos/ViaPost-io/viapost-python/releases/latest"


def verify(readme: str, release: dict[str, object]) -> None:
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("latest GitHub release has no valid version tag")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("latest GitHub release is not published and stable")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("latest GitHub release has no asset list")

    version = tag.removeprefix("v")
    wheel = f"viapost-{version}-py3-none-any.whl"
    sdist = f"viapost-{version}.tar.gz"
    published_assets = {
        asset.get("name")
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    if not {wheel, sdist}.issubset(published_assets):
        raise ValueError("latest GitHub release is missing the documented wheel or sdist")
    install_url = f"https://github.com/ViaPost-io/viapost-python/releases/download/{tag}/{wheel}"
    if f"pip install {install_url}" not in readme or sdist not in readme:
        raise ValueError("README does not reference the latest published release assets")


def main() -> None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "viapost-python-release-docs-check",
    }
    request = Request(LATEST_RELEASE_URL, headers=headers)
    with urlopen(request, timeout=20) as response:
        release = json.load(response)
    if not isinstance(release, dict):
        raise ValueError("latest GitHub release response is not an object")
    verify((ROOT / "README.md").read_text(encoding="utf-8"), release)
    print("README_RELEASE_ASSETS_VERIFIED=true")


if __name__ == "__main__":
    main()
