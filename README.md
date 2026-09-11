# ViaPost SDK for Python

Official typed Python client for the [ViaPost API](https://docs.viapost.io), with synchronous and
asynchronous APIs. Requires Python 3.10 or newer.

> Cliente Python oficial e tipado para a API ViaPost, com APIs síncrona e assíncrona. Requer
> Python 3.10 ou mais recente.

## Install / Instalação

GitHub Releases is the primary distribution channel. Install the exact wheel attached to a release
/ GitHub Releases é o canal principal de distribuição. Instale o wheel exato anexado à release:

```bash
pip install https://github.com/ViaPost-io/viapost-python/releases/download/v0.1.1/viapost-0.1.1-py3-none-any.whl
```

When that version is explicitly published to PyPI / Quando a versão for publicada explicitamente
no PyPI:

```bash
pip install viapost
```

The release also includes the source distribution (`viapost-0.1.1.tar.gz`) and checksums. The wheel
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
- `messages`: `list`, `retrieve`, `events`, `engagement`, `metrics`, `timeseries`
- `domains`: `list`, `create`, `retrieve`, `delete`, `dns`, `verify`, `rotate_dkim`
- `templates`: lifecycle, assets, preview, versions, publishing and revert
- `webhooks`: `list`, `create`, `delete`
- `automations`: lifecycle, drafts, runs and cancellation
- `usage.retrieve`

Every resource is available on both `ViaPost` and `AsyncViaPost`; async methods must be awaited.
Resource inputs and outputs use public `TypedDict` models rather than `Any`. Useful types such as
`SendRequest`, `SendResult`, `MessageList`, `CreateDomainRequest`, `CreateTemplateRequest`,
`CreateWebhookRequest`, `AutomationRunDetail`, and `MonthlyUsage` are exported from `viapost`.

## Reliability and errors / Confiabilidade e erros

- Default timeout: 60 seconds; override globally or per request.
- Maximum decoded response body: 10 MiB by default, enforced while streaming.
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

Error bodies and headers may contain request-related data. Redact them before forwarding errors to
shared logs or third-party observability services. Transport exceptions deliberately clear both
`__cause__` and `__context__` instead of retaining the underlying `httpx` exception, preventing
request headers from being reachable through exception chaining.

## OpenAPI contract / Contrato OpenAPI

The wheel includes the exact public OpenAPI 3.1 snapshot in `viapost/openapi.yaml`. Its SHA-256 is
exposed as `viapost.contract.OPENAPI_SHA256`; `viapost.contract.read_openapi()` reads the snapshot.
Version 0.1.0 vendors contract commit
`a5a2f018a3b4b47ed746325a8982f711171c3175` with SHA-256
`d1f223342ad1ca326ba716af6e508c78594e1b108958cce2ec4a1efd31a9773a`.

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
Publishing a GitHub Release automatically verifies, builds, attaches and attests the wheel and
source distribution. The locked release toolchain itself is also audited with hash enforcement.
PyPI publishing requires an explicit manual workflow opt-in, the protected `pypi` environment, and
successful GitHub asset attachment plus provenance attestation first.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
