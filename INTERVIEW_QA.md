# multi-tenant-saas-platform — interview questions and answers

[README](README.md) · [Project architecture](PROJECT_ARCHITECTURE.md)

Answers below use this repository’s files and implementation. They distinguish existing behavior from suggested extensions; source links let you verify each walkthrough.

## 1. What problem does multi-tenant-saas-platform address, and what can you demonstrate?

A local authorization server issues single-use codes with PKCE. The token carries the user's tenant and role. Every records call needs `X-Tenant` to match the token, and the role decides what the call may do.

I would demonstrate the linked implementation or examples and distinguish that evidence from any planned production features. Start with [`README.md`](README.md).

## 2. How is this repository organized?

- [`src/saas/main.py`](src/saas/main.py): Implementation or supporting configuration.
- [`src/saas/auth.py`](src/saas/auth.py): Authentication or access-control implementation.
- [`requirements.txt`](requirements.txt): Implementation or supporting configuration.
- [`web/src/App.tsx`](web/src/App.tsx): User interface code/assets.
- [`Dockerfile`](Dockerfile): Container build/service configuration.
- [`docker-compose.yml`](docker-compose.yml): Container build/service configuration.
- [`tests/test_saas.py`](tests/test_saas.py): Executable checks and regression examples.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml): GitHub Actions job definitions.

[PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) contains the component diagram and the implementation walkthrough.

## 3. Can you walk through `exchange` and explain the decision it makes?

The main walkthrough here is `exchange(grant_type, code, client_id, redirect_uri, code_verifier)` in [`src/saas/auth.py`](src/saas/auth.py#L52).

```python
def exchange(grant_type, code, client_id, redirect_uri, code_verifier):
    if grant_type != "authorization_code" or client_id != CLIENT_ID:
        raise AuthError("unsupported grant", 422)
    grant = CODES.pop(code, None)
    if grant is None:
        raise AuthError("unknown or already used code")
    if grant["expires"] < time.time():
        raise AuthError("code expired")
    if grant["redirect_uri"] != redirect_uri:
        raise AuthError("redirect_uri does not match the authorize request")
    if challenge_for(code_verifier) != grant["challenge"]:
        raise AuthError("code_verifier does not match the challenge")
    identity = USERS[grant["user"]]
    claims = {"sub": grant["user"], "tenant": identity["tenant"], "role": identity["role"]}
    return issue(claims)
```

The implementation calls `AuthError`, `CODES.pop`, `challenge_for`, `issue`, `time.time`. In an interview, trace those calls in execution order using a fixture input.

## 4. What responsibility does `authorize` have?

`authorize(client_id, redirect_uri, user, code_challenge, method='S256')` is defined in [`src/saas/auth.py`](src/saas/auth.py#L38).

Its return expressions include:

- `code`

It uses `AuthError`, `secrets.token_urlsafe`, `time.time`. This is the code path I would compare against the caller to explain responsibility boundaries.

## 5. What input validation and failure behavior are implemented?

Explicit failure paths include:

- `AuthError('unknown client', 422)` in [`src/saas/auth.py`](src/saas/auth.py#L40).
- `AuthError('redirect_uri is not registered', 422)` in [`src/saas/auth.py`](src/saas/auth.py#L42).
- `AuthError('unknown user', 422)` in [`src/saas/auth.py`](src/saas/auth.py#L44).
- `AuthError('PKCE with S256 is required', 422)` in [`src/saas/auth.py`](src/saas/auth.py#L46).
- `AuthError('unsupported grant', 422)` in [`src/saas/auth.py`](src/saas/auth.py#L54).
- `AuthError('unknown or already used code')` in [`src/saas/auth.py`](src/saas/auth.py#L57).
- `AuthError('code expired')` in [`src/saas/auth.py`](src/saas/auth.py#L59).

I would test both the condition that reaches each exception and the caller that translates it. An explicit raise does not mean every malformed input or dependency failure is handled.

## 6. Which test would you use to demonstrate correctness?

[`tests/test_saas.py`](tests/test_saas.py#L44) contains `test_tenant_cannot_read_the_other_tenant_or_delete`:

```python
def test_tenant_cannot_read_the_other_tenant_or_delete():
    headers = headers_for("ada", "north")
    assert [row["id"] for row in client.get("/records", headers=headers).json()["records"]] == ["rec-1"]
    assert client.get("/records", headers={**headers, "X-Tenant": "south"}).status_code == 403
    assert client.delete("/records/rec-1", headers=headers).status_code == 403
```

This is a concrete regression example from the repository. Its assertions establish that case; they do not establish behavior for every input or under production load.

## 7. What HTTP interface does the code expose?

- `GET /healthz` → `healthz` in [`src/saas/main.py`](src/saas/main.py#L69).
- `GET /oauth/authorize` → `authorize` in [`src/saas/main.py`](src/saas/main.py#L74).
- `POST /oauth/token` → `token` in [`src/saas/main.py`](src/saas/main.py#L80).
- `GET /me` → `me` in [`src/saas/main.py`](src/saas/main.py#L86).
- `GET /records` → `records` in [`src/saas/main.py`](src/saas/main.py#L92).
- `POST /records` → `create_record` in [`src/saas/main.py`](src/saas/main.py#L98).
- `DELETE /records/{record_id}` → `delete_record` in [`src/saas/main.py`](src/saas/main.py#L107).
- `GET /audit` → `audit` in [`src/saas/main.py`](src/saas/main.py#L118).

These are literal decorators. Application/router prefixes, authentication, and middleware must be checked in the corresponding setup code.

## 8. Where does state live, and what happens with multiple workers?

Module-level containers include `USERS`, `PERMISSIONS`, `CODES` in [`src/saas/auth.py`](src/saas/auth.py); `RECORDS`, `AUDIT` in [`src/saas/main.py`](src/saas/main.py).

These containers belong to a Python process. Inspect which are constant fixtures and which are mutated. Mutable process state needs an explicit shared-storage or synchronization strategy before multiple workers can provide consistent behavior.

## 9. How would another engineer reproduce your walkthrough?

Start from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

These commands follow repository manifests; environment setup and command results still need to be checked on the target machine.

## 10. What does automation verify, and what does it not prove?

Inspect [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for triggers, permissions, and job commands. I would name the checks that those definitions run and show the latest run separately. A workflow definition alone does not establish a successful deployment, security review, or production SLO.

## 11. How would you present this project in a Forward Deployed Engineer interview?

Start with the user and operational problem described in [`README.md`](README.md). Explain one constraint that changes the implementation, show the linked code or example, and walk through a success case and a failure case. Agree on a measurable acceptance criterion before expanding the solution, and leave a handoff with data boundaries and rollback ownership. Any proposed production or business metric should be identified as a target until measured.

## 12. What is the input-to-output contract of `exchange`?

In [`src/saas/auth.py`](src/saas/auth.py#L52), `exchange(grant_type, code, client_id, redirect_uri, code_verifier)` receives the inputs. The function computes these intermediate values:

- `grant = CODES.pop(code, None)`
- `identity = USERS[grant['user']]`
- `claims = {'sub': grant['user'], 'tenant': identity['tenant'], 'role': identity['role']}`

Its result is defined by:

- `issue(claims)`

## 13. Which decision rules or boundary conditions should an interviewer challenge?

The implementation in [`src/saas/auth.py`](src/saas/auth.py#L52) branches on:

- `grant_type != 'authorization_code' or client_id != CLIENT_ID`
- `grant is None`
- `grant['expires'] < time.time()`
- `grant['redirect_uri'] != redirect_uri`
- `challenge_for(code_verifier) != grant['challenge']`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

## 14. What does `web/src/App.tsx` own?

[`web/src/App.tsx`](web/src/App.tsx) defines `App`, `headers`, `load`, `create`. Its imports include `react`.

Trace these definitions and imports to explain the module boundary. Relative imports identify project code; package imports should be checked against the nearest manifest.
