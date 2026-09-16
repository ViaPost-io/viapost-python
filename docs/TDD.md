# TDD evidence

This SDK is implemented behavior-by-behavior using Red → Green → Refactor.

## Observable behavior plan

1. Construction validates the API key, secure base URL, timeout, separate JSON/raw response limits,
   and retry settings.
2. Sync requests send Bearer authentication, JSON headers/body, query parameters, and a 60-second default timeout.
3. Async requests provide the same wire behavior and lifecycle as the sync client.
4. API failures expose typed status, request ID, response body, method, URL, and headers.
5. Timeouts, connection failures, and oversized responses have distinct typed exceptions.
6. Automatic retries apply only to GET/HEAD for 429 and 5xx responses and respect Retry-After.
7. Mutating requests are never automatically retried.
8. `send.create` validates and forwards an idempotency key and normalizes nullable accepted/rejected lists.
9. Path identifiers are percent-encoded and reject empty, `.` and `..` values.
10. Sync and async resources expose send, messages, inbound messages, suppressions, domains,
    templates, webhooks, automations, and usage operations from the public authenticated contract.
11. Public request/response types, version metadata, and the vendored OpenAPI snapshot ship in wheel and sdist artifacts.
12. Contract drift, lint, typing, coverage, artifact verification, and release workflows are reproducible and least-privileged.
13. Protected headers cannot be overridden case-insensitively, redirects are never followed, and all non-2xx statuses are typed errors.
14. Transport errors do not retain the underlying request (and therefore cannot retain the API key), while API and idempotency keys are header-safe visible ASCII.
15. Compressed response sizes are enforced against decoded streamed bytes, not encoded `Content-Length`.
16. Every public resource method has a concrete request and response type derived from the OpenAPI schema.
17. One-time webhook secrets require explicit property access and are redacted from string, log,
    dictionary, and pickle representations.
18. API errors recursively redact credentials echoed by an untrusted backend.
19. Webhook callbacks reject client-detectable SSRF inputs while server-side DNS validation remains
    authoritative.
20. Contract downloads are incrementally bounded and restricted to approved HTTPS redirect targets.
21. Releases verify, build and attest before strict draft recovery/publication; PyPI can run only
    after the protected GitHub release job succeeds.

## Cycle log

The command output for the first Red and final Green runs is recorded in `docs/tdd-red.txt` and
`docs/tdd-green.txt`. Each subsequent behavior was added as a focused test, observed failing for
the expected missing behavior, then implemented minimally before proceeding. Refactoring followed
with the full suite green.
