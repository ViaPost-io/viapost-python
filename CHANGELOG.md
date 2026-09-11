# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions
follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/ViaPost-io/viapost-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ViaPost-io/viapost-python/releases/tag/v0.1.0
