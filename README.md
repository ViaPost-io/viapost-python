# ViaPost SDK for Python

Official typed Python client for the [ViaPost API](https://docs.viapost.io), with synchronous and
asynchronous APIs. Requires Python 3.10 or newer.

> Cliente Python oficial e tipado para a API ViaPost, com APIs síncrona e assíncrona. Requer
> Python 3.10 ou mais recente.

## Install / Instalação

GitHub Releases is the primary distribution channel. Install the exact wheel attached to a release
/ GitHub Releases é o canal principal de distribuição. Instale o wheel exato anexado à release:

```bash
pip install https://github.com/ViaPost-io/viapost-python/releases/download/v0.2.1/viapost-0.2.1-py3-none-any.whl
```

When that version is explicitly published to PyPI / Quando a versão for publicada explicitamente
no PyPI:

```bash
pip install viapost
```

The release also includes the source distribution (`viapost-0.2.1.tar.gz`) and checksums. The wheel
is preferred because installation does not need to execute a build backend. GitHub also records
build provenance attestations for both artifacts.

## Quickstart / Início rápido

```python
import os

from viapost import ViaPost

with ViaPost(api_key=os.environ["VIAPOST_API_KEY"]) as viapost:
    result = viapost.send.create(
        {
            "from": "hello@your-domain.example",
            "to": ["person@example.com"],
            "subject": "Hello from ViaPost",
            "html": "<strong>Hello!</strong>",
            "text": "Hello!",
        },
        idempotency_key="order-123-welcome-email",
    )

print(result["accepted"])
```

Async / Assíncrono:

```python
import os

from viapost import AsyncViaPost


async def send_email() -> None:
    async with AsyncViaPost(api_key=os.environ["VIAPOST_API_KEY"]) as viapost:
        result = await viapost.send.create(
            {"from": "hello@example.com", "to": ["person@example.com"], "subject": "Hello"}
        )
        print(result["accepted"])
```

The client sends `Authorization: Bearer …` to `https://api.viapost.io`. A custom `base_url` must use
HTTPS; plain HTTP is accepted only for loopback development hosts such as
`http://localhost:15080`. URLs containing credentials are rejected.

## Resources / Recursos

- `send.create`
- `messages`: `list`, `retrieve`, `raw`, `events`, `engagement`, `metrics`, `timeseries`
- `inbound_messages`: `list`, `retrieve`, `raw`
- `suppressions`: `list`, `create`, `retrieve`, `release`, `import_csv`, `export_csv`
- `domains`: `list`, `create`, `retrieve`, `delete`, `dns`, `verify`, `rotate_dkim`
- `templates`: lifecycle, assets, preview, versions, publishing and revert
- `webhooks`: lifecycle, deliveries, replay, secret rotation and test delivery
- `automations`: lifecycle, drafts, runs and cancellation
- `usage.retrieve`

Every resource is available on both `ViaPost` and `AsyncViaPost`; async methods must be awaited.
Resource inputs and outputs use public `TypedDict` models rather than `Any`. Useful types such as
`SendRequest`, `SendResult`, `MessageList`, `CreateDomainRequest`, `CreateTemplateRequest`,
`CreateWebhookRequest`, `CreateSuppressionRequest`, `InboundMessageDetail`,
`WebhookDeliveryDetail`, `AutomationRunDetail`, and `MonthlyUsage` are exported from `viapost`.

Webhook creation and secret rotation return redaction-safe objects. Access a newly issued secret
deliberately with `result.secret`; `str(result)`, `repr(result)`, and `result.to_dict()` redact it.
Callback URL checks reject credentials, fragments, localhost and non-public IP literals. The API
remains authoritative and also resolves DNS immediately before accepting or delivering callbacks.

The three public status-subscription endpoints are intentionally not exposed by `ViaPost` or
`AsyncViaPost`. They are unauthenticated double-opt-in browser flows hosted exclusively at
`status.viapost.io`; routing them through an authenticated SDK client would unnecessarily send an
API key to a different host. Use the status page to subscribe, confirm, or unsubscribe.

## Reliability and errors / Confiabilidade e erros

- Default timeout: 60 seconds; override globally or per request.
- Maximum decoded JSON/error body: 10 MiB by default, enforced while streaming.
- Raw RFC 822 message downloads have an independent 40 MiB default limit; configure
  `max_raw_response_bytes` up to the defensive 64 MiB ceiling without increasing JSON/error limits.
- Automatic retries: only GET/HEAD responses with HTTP 429 or 5xx; default is two retries.
- Mutating requests are never retried automatically.
- API keys and `send.create` idempotency keys must use visible ASCII, making them safe for HTTP
  headers; idempotency keys are limited to 1–255 bytes.
- Resource identifiers are safely percent-encoded.
- Redirects are never followed. Every non-2xx response, including 1xx and 3xx, raises
  `ViaPostAPIError`.

```python
from viapost import ViaPostAPIError, ViaPostTimeoutError

try:
    message = viapost.messages.retrieve("message-id")
except ViaPostAPIError as error:
    print(error.status, error.request_id, error.body)
except ViaPostTimeoutError as error:
    print(error.timeout)
```

Error messages, bodies and response headers are recursively sanitized for credentials and common
secret/token fields before they are exposed by `ViaPostAPIError`. Application data can still be
sensitive, so use normal care before forwarding errors to third-party services. Transport exceptions deliberately clear both
`__cause__` and `__context__` instead of retaining the underlying `httpx` exception, preventing
request headers from being reachable through exception chaining.

## OpenAPI contract / Contrato OpenAPI

The wheel includes the exact public OpenAPI 3.1 snapshot in `viapost/openapi.yaml`. Its SHA-256 is
exposed as `viapost.contract.OPENAPI_SHA256`; `viapost.contract.read_openapi()` reads the snapshot.
Version 0.2.1 vendors the semantic snapshot published at
`https://docs.viapost.io/openapi/public.yaml` with SHA-256
`4296cf369c8a2b1e27f215fddc36dbafb4203aa35c509095df1048243b8da847`.

```bash
python scripts/check_contract.py
```

The OpenAPI document remains subject to the terms declared inside it. SDK source code is MIT
licensed.

## Development / Desenvolvimento

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy
pytest --cov=viapost --cov-report=term-missing
python -m build
twine check dist/*
pip-audit --requirement requirements/runtime.txt
```

Release builds install a fully hash-locked toolchain from
`.github/requirements/release.txt`; isolated artifact tests install runtime dependencies from the
separate `.github/requirements/runtime.txt` hash lock and install the wheel with `--no-deps`.
Checksums and immutable workflow artifacts are created before that consumer installation.
Pushing a version tag (or manually dispatching its existing tag) verifies and builds first, creates
provenance attestations, then strictly creates or recovers a matching draft without overwriting any
asset before publishing it. A later manual PyPI continuation accepts an existing public release only
when its remote tag commit, complete asset set, and every asset hash match the newly verified build.
The locked release toolchain itself is audited with hash enforcement.
PyPI publishing requires an explicit manual workflow opt-in, the protected `pypi` environment, and
a verified, already-published GitHub Release plus provenance attestation first.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
