from __future__ import annotations

import hashlib

from viapost.contract import OPENAPI_SHA256, read_openapi


def test_vendored_openapi_snapshot_is_verifiable() -> None:
    source = read_openapi()
    assert source.startswith("openapi: 3.1.1\n")
    assert hashlib.sha256(source.encode()).hexdigest() == OPENAPI_SHA256
