from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
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
