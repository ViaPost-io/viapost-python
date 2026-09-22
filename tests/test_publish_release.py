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


def test_release_recovers_oldest_of_duplicate_empty_stable_drafts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        assert capture is True
        if args[-1] == "repos/acme/sdk/releases/tags/v0.2.0":
            return CompletedProcess(args, 1, stdout=b"", stderr=b"HTTP 404")
        return CompletedProcess(
            args,
            0,
            stdout=(
                b'[[{"id":9,"tag_name":"v0.2.0","draft":true,"prerelease":false,"assets":[]},'
                b'{"id":4,"tag_name":"v0.2.0","draft":true,"prerelease":false,"assets":[]}]]'
            ),
            stderr=b"",
        )

    monkeypatch.setattr(publish_release, "_run", fake_run)

    assert publish_release._release("acme/sdk", "v0.2.0") == {
        "id": 4,
        "tag_name": "v0.2.0",
        "draft": True,
        "prerelease": False,
        "assets": [],
    }


def test_create_draft_uses_api_response_without_tag_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: str, capture: bool = False) -> CompletedProcess[bytes]:
        assert capture is True
        assert args == (
            "gh",
            "api",
            "--method",
            "POST",
            "repos/acme/sdk/releases",
            "-f",
            "tag_name=v0.2.0",
            "-f",
            "target_commitish=abc123",
            "-f",
            "name=v0.2.0",
            "-F",
            "draft=true",
            "-F",
            "prerelease=false",
            "-F",
            "generate_release_notes=true",
        )
        return CompletedProcess(args, 0, stdout=b'{"id":7,"tag_name":"v0.2.0"}', stderr=b"")

    monkeypatch.setattr(publish_release, "_run", fake_run)

    assert publish_release._create_draft("acme/sdk", "v0.2.0", "abc123") == {
        "id": 7,
        "tag_name": "v0.2.0",
    }


def test_publish_uses_created_release_id_without_reading_draft_by_tag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel = tmp_path / "viapost-0.2.0-py3-none-any.whl"
    checksums = tmp_path / "SHA256SUMS"
    wheel.write_bytes(b"wheel")
    checksums.write_bytes(b"checksums")
    created = {
        "id": 7,
        "tag_name": "v0.2.0",
        "draft": True,
        "prerelease": False,
        "assets": [],
    }
    recovered = {
        **created,
        "assets": [
            {"id": 11, "name": wheel.name},
            {"id": 12, "name": checksums.name},
        ],
    }
    published = {**recovered, "draft": False}
    uploaded: list[tuple[int, str]] = []

    monkeypatch.setenv("GH_REPO", "acme/sdk")
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setattr(publish_release, "_tag_commit", lambda *_: "abc123")
    monkeypatch.setattr(publish_release, "_release", lambda *_: None)
    monkeypatch.setattr(publish_release, "_create_draft", lambda *_: created)
    monkeypatch.setattr(
        publish_release,
        "_upload_asset",
        lambda _repo, release_id, path: uploaded.append((release_id, path.name)),
    )
    monkeypatch.setattr(publish_release, "_release_by_id", lambda *_: recovered)
    monkeypatch.setattr(publish_release, "_publish_draft", lambda *_: published)
    monkeypatch.setattr(publish_release, "_require_same_asset", lambda *_: None)

    publish_release.publish("v0.2.0", "abc123", [wheel, checksums])

    assert uploaded == [(7, wheel.name), (7, checksums.name)]


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
