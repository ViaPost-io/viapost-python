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
from urllib.parse import quote


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
    if "HTTP 404" not in error:
        raise RuntimeError("unable to query the GitHub release")

    # GitHub does not resolve a draft by tag until it becomes public. Recover
    # only one exact tag across every authenticated releases page and let the
    # callers validate every other invariant (state, commit and artifacts)
    # before it is reused. --slurp keeps paginated JSON unambiguous.
    drafts = _run(
        "gh",
        "api",
        "--paginate",
        "--slurp",
        f"repos/{repo}/releases?per_page=100",
        capture=True,
    )
    if drafts.returncode != 0:
        raise RuntimeError("unable to list GitHub releases for draft recovery")
    document = json.loads(drafts.stdout)
    if not isinstance(document, list) or any(not isinstance(page, list) for page in document):
        raise RuntimeError("GitHub releases listing has an unexpected shape")
    matches = [
        candidate
        for page in document
        for candidate in page
        if isinstance(candidate, dict) and candidate.get("tag_name") == tag
    ]
    if len(matches) > 1:
        # GitHub permits several unpublished drafts for a tag. They are safe
        # to recover only while each is an empty, stable draft with an ID; any
        # uploaded asset would make choosing a canonical draft ambiguous.
        if not all(
            candidate.get("draft") is True
            and candidate.get("prerelease") is False
            and isinstance(candidate.get("id"), int)
            and candidate.get("assets") == []
            for candidate in matches
        ):
            raise RuntimeError("multiple GitHub releases claim the requested tag")
        return min(matches, key=lambda candidate: cast(int, candidate["id"]))
    return cast(dict[str, object], matches[0]) if matches else None


def _release_id(release: dict[str, object]) -> int:
    release_id = release.get("id")
    if not isinstance(release_id, int):
        raise ValueError("release metadata does not contain a valid ID")
    return release_id


def _release_by_id(repo: str, release_id: int) -> dict[str, object]:
    result = _run("gh", "api", f"repos/{repo}/releases/{release_id}", capture=True)
    if result.returncode != 0:
        raise RuntimeError("unable to read the GitHub release by ID")
    document = json.loads(result.stdout)
    if not isinstance(document, dict):
        raise RuntimeError("GitHub release lookup returned an unexpected shape")
    return cast(dict[str, object], document)


def _create_draft(repo: str, tag: str, source_sha: str) -> dict[str, object]:
    result = _run(
        "gh",
        "api",
        "--method",
        "POST",
        f"repos/{repo}/releases",
        "-f",
        f"tag_name={tag}",
        "-f",
        f"target_commitish={source_sha}",
        "-f",
        f"name={tag}",
        "-F",
        "draft=true",
        "-F",
        "prerelease=false",
        "-F",
        "generate_release_notes=true",
        capture=True,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to create the GitHub draft release")
    document = json.loads(result.stdout)
    if not isinstance(document, dict):
        raise RuntimeError("GitHub draft creation returned an unexpected shape")
    return cast(dict[str, object], document)


def _upload_asset(repo: str, release_id: int, path: Path) -> None:
    result = _run(
        "gh",
        "api",
        "--method",
        "POST",
        f"repos/{repo}/releases/{release_id}/assets?name={quote(path.name, safe='')}",
        "-H",
        "Content-Type: application/octet-stream",
        "--input",
        str(path),
        capture=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"unable to upload release asset: {path.name}")


def _publish_draft(repo: str, release_id: int) -> dict[str, object]:
    result = _run(
        "gh",
        "api",
        "--method",
        "PATCH",
        f"repos/{repo}/releases/{release_id}",
        "-F",
        "draft=false",
        capture=True,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to publish the verified GitHub release")
    document = json.loads(result.stdout)
    if not isinstance(document, dict):
        raise RuntimeError("GitHub release publication returned an unexpected shape")
    return cast(dict[str, object], document)


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
        # Preserve the POST response rather than re-reading a draft by tag:
        # GitHub intentionally hides drafts from that endpoint and can lag
        # immediately after creation.
        release = _create_draft(repo, tag, source_sha)

    existing = validate_draft(
        release,
        tag=tag,
        source_sha=source_sha,
        tag_commit_sha=_tag_commit(repo, tag),
        expected_names=set(by_name),
    )
    release_id = _release_id(release)
    for name, path in by_name.items():
        if name in existing:
            _require_same_asset(repo, existing[name], path)
            continue
        _upload_asset(repo, release_id, path)

    recovered = _release_by_id(repo, release_id)
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

    published = _publish_draft(repo, release_id)
    if published.get("draft") is not False:
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
