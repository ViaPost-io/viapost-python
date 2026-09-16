"""Create or strictly recover a GitHub draft release, then publish it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast


def _run(*args: str, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
    )


def _release(repo: str, tag: str) -> dict[str, object] | None:
    result = _run("gh", "api", f"repos/{repo}/releases/tags/{tag}", capture=True)
    if result.returncode == 0:
        return cast(dict[str, object], json.loads(result.stdout))
    error = result.stderr.decode("utf-8", errors="replace")
    if "HTTP 404" in error:
        return None
    raise RuntimeError("unable to query the GitHub release")


def _tag_commit(repo: str, tag: str) -> str:
    result = _run("gh", "api", f"repos/{repo}/commits/{tag}", capture=True)
    if result.returncode != 0:
        raise RuntimeError("unable to resolve the remote release tag")
    document = json.loads(result.stdout)
    sha = document.get("sha") if isinstance(document, dict) else None
    if not isinstance(sha, str) or not sha:
        raise RuntimeError("remote release tag did not resolve to a commit")
    return sha


def _assets(release: dict[str, object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw in cast(list[object], release.get("assets", [])):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise ValueError("release contains malformed asset metadata")
        name = cast(str, raw["name"])
        asset_id = raw.get("id")
        if name in result or not isinstance(asset_id, int):
            raise ValueError("release contains duplicate or malformed assets")
        result[name] = asset_id
    return result


def validate_draft(
    release: dict[str, object],
    *,
    tag: str,
    source_sha: str,
    tag_commit_sha: str,
    expected_names: set[str],
) -> dict[str, int]:
    """Fail closed unless an existing release is the exact recoverable draft."""

    if release.get("tag_name") != tag:
        raise ValueError("draft tag does not match the requested release")
    if release.get("draft") is not True or release.get("prerelease") is not False:
        raise ValueError("release recovery is allowed only for an unpublished non-prerelease draft")
    if tag_commit_sha != source_sha:
        raise ValueError("remote tag commit does not match the verified source")
    assets = _assets(release)
    unexpected = set(assets) - expected_names
    if unexpected:
        raise ValueError(f"draft contains unexpected assets: {sorted(unexpected)!r}")
    return assets


def validate_published(
    release: dict[str, object],
    *,
    tag: str,
    source_sha: str,
    tag_commit_sha: str,
    expected_names: set[str],
) -> dict[str, int]:
    """Allow continuation only for the exact already-published stable release."""

    if release.get("tag_name") != tag:
        raise ValueError("published release tag does not match the requested release")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("published release state does not match the requested stable release")
    if tag_commit_sha != source_sha:
        raise ValueError("remote tag commit does not match the verified source")
    assets = _assets(release)
    if set(assets) != expected_names:
        raise ValueError("published release assets do not exactly match verified artifacts")
    return assets


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_asset(repo: str, asset_id: int) -> bytes:
    result = _run(
        "gh",
        "api",
        f"repos/{repo}/releases/assets/{asset_id}",
        "-H",
        "Accept: application/octet-stream",
        capture=True,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to download an existing release asset")
    return result.stdout


def _require_same_asset(repo: str, asset_id: int, local: Path) -> None:
    remote = _download_asset(repo, asset_id)
    if hashlib.sha256(remote).hexdigest() != _sha256(local):
        raise ValueError(f"existing release asset differs from verified artifact: {local.name}")


def publish(tag: str, source_sha: str, paths: list[Path]) -> None:
    repo = os.environ.get("GH_REPO", "")
    if not repo or not os.environ.get("GH_TOKEN"):
        raise ValueError("GH_REPO and GH_TOKEN are required")
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("every release artifact must be an existing file")
    by_name = {path.name: path for path in paths}
    if len(by_name) != len(paths):
        raise ValueError("release artifact names must be unique")

    tag_commit_sha = _tag_commit(repo, tag)
    release = _release(repo, tag)
    if release is not None and release.get("draft") is False:
        published_assets = validate_published(
            release,
            tag=tag,
            source_sha=source_sha,
            tag_commit_sha=tag_commit_sha,
            expected_names=set(by_name),
        )
        for name, asset_id in published_assets.items():
            _require_same_asset(repo, asset_id, by_name[name])
        return
    if release is None:
        created = _run(
            "gh",
            "release",
            "create",
            tag,
            "--draft",
            "--verify-tag",
            "--target",
            source_sha,
            "--title",
            tag,
            "--generate-notes",
        )
        if created.returncode != 0:
            raise RuntimeError("unable to create the GitHub draft release")
        release = _release(repo, tag)
        if release is None:
            raise RuntimeError("created GitHub draft release could not be read back")

    existing = validate_draft(
        release,
        tag=tag,
        source_sha=source_sha,
        tag_commit_sha=_tag_commit(repo, tag),
        expected_names=set(by_name),
    )
    for name, path in by_name.items():
        if name in existing:
            _require_same_asset(repo, existing[name], path)
            continue
        uploaded = _run("gh", "release", "upload", tag, str(path))
        if uploaded.returncode != 0:
            raise RuntimeError(f"unable to upload release asset: {name}")

    recovered = _release(repo, tag)
    if recovered is None:
        raise RuntimeError("draft release disappeared during publication")
    recovered_assets = validate_draft(
        recovered,
        tag=tag,
        source_sha=source_sha,
        tag_commit_sha=_tag_commit(repo, tag),
        expected_names=set(by_name),
    )
    if set(recovered_assets) != set(by_name):
        raise ValueError("draft assets are incomplete after upload")
    for name, asset_id in recovered_assets.items():
        _require_same_asset(repo, asset_id, by_name[name])

    edited = _run("gh", "release", "edit", tag, "--draft=false")
    if edited.returncode != 0:
        raise RuntimeError("unable to publish the verified GitHub release")
    published = _release(repo, tag)
    if published is None or published.get("draft") is not False:
        raise RuntimeError("GitHub release did not become public")
    published_assets = validate_published(
        published,
        tag=tag,
        source_sha=source_sha,
        tag_commit_sha=_tag_commit(repo, tag),
        expected_names=set(by_name),
    )
    for name, asset_id in published_assets.items():
        _require_same_asset(repo, asset_id, by_name[name])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        publish(args.tag, args.source_sha, args.artifacts)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
