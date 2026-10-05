# Multi-tenant SaaS platform

<!-- project-guide:start -->
## Project guide

[Project architecture](PROJECT_ARCHITECTURE.md) · [Interview questions and answers](INTERVIEW_QA.md)

Use the architecture document for the component diagram, implementation boundaries, and verification entry points. The interview guide includes source-backed answers and project walkthroughs.

### Implementation map

| Component | Responsibility |
| --- | --- |
| [`src/saas/main.py`](src/saas/main.py) | HTTP handlers: `GET /healthz`, `GET /oauth/authorize`, `POST /oauth/token`, `GET /me`, `GET /records` |
| [`src/saas/auth.py`](src/saas/auth.py) | Functions: `challenge_for`, `authorize`, `exchange`, `issue`, `decode`, `require`, `__init__` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`web/src/App.tsx`](web/src/App.tsx) | User interface code/assets |
| [`Dockerfile`](Dockerfile) | Container build/service configuration |
| [`docker-compose.yml`](docker-compose.yml) | Container build/service configuration |
| [`tests/test_saas.py`](tests/test_saas.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |

### Local setup and verification

From the repository root (the commands follow the checked-in manifests):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

To serve the FastAPI application locally, install the server separately if it is not already available:

```bash
python -m pip install uvicorn
PYTHONPATH=src python -m uvicorn saas.main:app --reload
```

<!-- project-guide:end -->

Level: Intermediate+

Skills: React, FastAPI, tenant isolation, OAuth authorization code with PKCE, RBAC, audit

A local authorization server issues single-use codes with PKCE. The token carries the user's tenant and role. Every records call needs `X-Tenant` to match the token, and the role decides what the call may do.

| User | Tenant | Role | May |
| --- | --- | --- | --- |
| ada | north | member | read, create |
| grace | north | admin | read, create, delete, read the audit log |
| linus | south | viewer | read |

This is not a Google login. The client is `local-console`, the registered redirect is `http://localhost:5173/callback`, and the user is picked by name so the tests run without a browser. Redis is not required. The record list stands in for the tenant database.

```bash
pip install -r requirements.txt
pytest -q
docker compose up --build
```

## The OAuth flow

1. The client makes a random `code_verifier` and sends its SHA-256 `code_challenge` to `GET /oauth/authorize`.
2. The server returns a code that expires in 5 minutes and echoes `state`.
3. `POST /oauth/token` with the code, the same `redirect_uri`, and the original `code_verifier`.

The code works once. A replay, a wrong verifier, an unregistered redirect, or a redirect that differs between the two steps is refused.

## Endpoints

| Method and path | Needs |
| --- | --- |
| `GET /me` | Any valid token. Returns the role and its permissions |
| `GET /records` | read |
| `POST /records` | create. The record is stamped with the caller's tenant, never the body's |
| `DELETE /records/{id}` | delete. Another tenant's id is 404 |
| `GET /audit` | audit. Only this tenant's create and delete events |

## Ops plane

Workspaces, tenant isolation, job approval, and audit live under `/v1`. Production apply is refused. See `docs/ARCHITECTURE.md`.
