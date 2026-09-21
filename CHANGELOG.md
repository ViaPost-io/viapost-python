# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-09-18

### Changed

- Synchronize the vendored public OpenAPI snapshot with the published contract, including contacts
  import, tracking domains, audience segments, inbound configuration, and broadcast foundations.
  This does not claim new high-level client methods for endpoints outside the typed resource layer.
- Bump the public SDK version for the changed contract snapshot.

## [0.2.0] - 2026-09-16

### Added

- Add typed synchronous and asynchronous resources for inbound messages, message source downloads,
  suppressions, and the complete webhook operations surface.
- Add bounded binary responses and CSV import/export transport support.

### Changed

- **Breaking:** webhook creation and secret rotation now return redaction-safe objects; read the
  one-time secret explicitly through `.secret` instead of dictionary indexing. Their `repr`,
  `str`, pickle state, and `to_dict()` representations redact the secret.
- Raw RFC 822 downloads use an independent 40 MiB default limit (configurable up to 64 MiB), while
  JSON responses and API error bodies retain the 10 MiB limit.
- Release publication now attests before publishing, recovers drafts without overwrites, and permits
  a later PyPI continuation only after exact tag, asset-set, and asset-hash verification.

- Synchronize the vendored OpenAPI snapshot with the public contract and make the scheduled drift
  gate target the public documentation URL explicitly.
- Document why the unauthenticated status-subscription browser flow is not part of the authenticated
  SDK client.

## [0.1.3] - 2026-09-11

### Fixed

- Build the SDK as a regular wheel during the release gate, avoiding the optional `editables`
  backend dependency while keeping the release toolchain hash-locked.

## [0.1.2] - 2026-09-11

### Fixed

- Make release asset attachment repository-explicit in checkout-free jobs.

## [0.1.1] - 2026-09-11

### Fixed

- Build the hash-locked release toolchain from Linux so platform-specific publishing dependencies
  are reproducible in GitHub Actions.

## [0.1.0] - 2026-09-11

### Added

- Initial synchronous and asynchronous ViaPost API clients.
- Send, messages, domains, templates, webhooks, automations, and usage resources.
- Typed errors, safe URL/path handling, bounded responses, conservative retries, and idempotent send.
- Verifiable OpenAPI snapshot and GitHub/PyPI release pipelines.

[Unreleased]: https://github.com/ViaPost-io/viapost-python/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ViaPost-io/viapost-python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ViaPost-io/viapost-python/releases/tag/v0.1.0
