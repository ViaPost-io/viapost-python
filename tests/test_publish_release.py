from __future__ import annotations

import sys
from pathlib import Path
from subprocess import CompletedProcess

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from scripts import publish_release
from scripts.publish_release import validate_draft, validate_published


def _release(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "tag_name": "v0.2.0",
        "draft": True,
        "prerelease": False,
        "target_commitish": "abc123",
        "assets": [{"id": 1, "name": "viapost.whl"}],
    }
    value.update(overrides)
    return value


def test_draft_recovery_accepts_only_matching_partial_assets() -> None:
    assert validate_draft(
        _release(),
        tag="v0.2.0",
        source_sha="abc123",
        tag_commit_sha="abc123",
        expected_names={"viapost.whl", "SHA256SUMS"},
    ) == {"viapost.whl": 1}


def test_release_recovers_exact_draft_when_github_hides_drafts_by_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        assert capture is True
        if args[-1] == "repos/acme/sdk/releases/tags/v0.2.0":
            return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 404")
        assert args[-3:] == (
            "--paginate",
            "--slurp",
            "repos/acme/sdk/releases?per_page=100",
        )
        return CompletedProcess(
            args,
            0,
            stdout=b'[[{"tag_name":"v0.1.0"}],[{"tag_name":"v0.2.0","draft":true}]]',
            stderr=b"",
        )

    monkeypatch.setattr(publish_release, "_run", fake_run)

    assert publish_release._release("acme/sdk", "v0.2.0") == {
        "tag_name": "v0.2.0",
        "draft": True,
    }


def test_release_returns_none_when_draft_listing_has_no_matching_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        assert capture is True
        if args[-1] == "repos/acme/sdk/releases/tags/v0.2.0":
            return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 404")
        assert args[-3:] == (
            "--paginate",
            "--slurp",
            "repos/acme/sdk/releases?per_page=100",
        )
        return CompletedProcess(args, 0, stdout=b'[[{"tag_name":"v0.1.0"}]]', stderr=b"")

    monkeypatch.setattr(publish_release, "_run", fake_run)

    assert publish_release._release("acme/sdk", "v0.2.0") is None


def test_release_rejects_duplicate_tags_in_draft_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        assert capture is True
        if args[-1] == "repos/acme/sdk/releases/tags/v0.2.0":
            return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 404")
        assert args[-3:] == (
            "--paginate",
            "--slurp",
            "repos/acme/sdk/releases?per_page=100",
        )
        return CompletedProcess(
            args,
            0,
            stdout=b'[[{"tag_name":"v0.2.0"}],[{"tag_name":"v0.2.0"}]]',
            stderr=b"",
        )

    monkeypatch.setattr(publish_release, "_run", fake_run)

    with pytest.raises(RuntimeError, match="multiple GitHub releases"):
        publish_release._release("acme/sdk", "v0.2.0")


def test_release_rejects_failed_draft_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        assert capture is True
        if args[-1] == "repos/acme/sdk/releases/tags/v0.2.0":
            return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 404")
        assert args[-3:] == (
            "--paginate",
            "--slurp",
            "repos/acme/sdk/releases?per_page=100",
        )
        return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 500")

    monkeypatch.setattr(publish_release, "_run", fake_run)

    with pytest.raises(RuntimeError, match="unable to list GitHub releases"):
        publish_release._release("acme/sdk", "v0.2.0")


def test_release_rejects_non_paginated_release_listing_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        if args[-1] == "repos/acme/sdk/releases/tags/v0.2.0":
            return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 404")
        return CompletedProcess(args, 0, stdout=b'[{"tag_name":"v0.2.0"}]', stderr=b"")

    monkeypatch.setattr(publish_release, "_run", fake_run)

    with pytest.raises(RuntimeError, match="unexpected shape"):
        publish_release._release("acme/sdk", "v0.2.0")


@pytest.mark.parametrize(
    "release",
    [
        _release(draft=False),
        _release(prerelease=True),
        _release(tag_name="v9.9.9"),
        _release(assets=[{"id": 2, "name": "unexpected"}]),
        _release(assets=[{"id": 1, "name": "viapost.whl"}, {"id": 2, "name": "viapost.whl"}]),
    ],
)
def test_draft_recovery_rejects_metadata_asset_or_state_mismatches(
    release: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        validate_draft(
            release,
            tag="v0.2.0",
            source_sha="abc123",
            tag_commit_sha="abc123",
            expected_names={"viapost.whl", "SHA256SUMS"},
        )


def test_draft_recovery_rejects_a_moved_remote_tag() -> None:
    with pytest.raises(ValueError, match="remote tag"):
        validate_draft(
            _release(target_commitish="main"),
            tag="v0.2.0",
            source_sha="abc123",
            tag_commit_sha="moved",
            expected_names={"viapost.whl"},
        )


def test_published_release_continuation_requires_exact_assets_and_source() -> None:
    release = _release(draft=False)
    assert validate_published(
        release,
        tag="v0.2.0",
        source_sha="abc123",
        tag_commit_sha="abc123",
        expected_names={"viapost.whl"},
    ) == {"viapost.whl": 1}
    with pytest.raises(ValueError, match="exactly"):
        validate_published(
            release,
            tag="v0.2.0",
            source_sha="abc123",
            tag_commit_sha="abc123",
            expected_names={"viapost.whl", "SHA256SUMS"},
        )
