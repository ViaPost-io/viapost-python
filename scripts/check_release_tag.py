"""Verify a release tag matches project metadata exactly."""

from __future__ import annotations

import sys
from pathlib import Path

import tomllib


def main(tag: str) -> int:
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    expected = f"v{project['project']['version']}"
    if tag != expected:
        print(
            f"Release tag must be exactly {expected}; received {tag or '<empty>'}",
            file=sys.stderr,
        )
        return 1
    print(f"Release tag {tag} matches pyproject.toml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
