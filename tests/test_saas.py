import secrets

import pytest
from fastapi.testclient import TestClient

from saas import auth
from saas.main import app, seed

client = TestClient(app)
REDIRECT = auth.REDIRECT_URI


@pytest.fixture(autouse=True)
def fresh():
    seed()


def code_for(user, verifier):
    params = {
        "client_id": "local-console",
        "redirect_uri": REDIRECT,
        "user": user,
        "code_challenge": auth.challenge_for(verifier),
        "state": "s",
    }
    response = client.get("/oauth/authorize", params=params)
    assert response.json()["state"] == "s"
    return response.json()["code"]


def exchange(code, verifier, redirect=REDIRECT):
    return client.post(
        "/oauth/token",
        json={"grant_type": "authorization_code", "code": code, "client_id": "local-console", "redirect_uri": redirect, "code_verifier": verifier},
    )


def headers_for(user, tenant):
    verifier = secrets.token_urlsafe(48)
    token = exchange(code_for(user, verifier), verifier).json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Tenant": tenant}


def test_tenant_cannot_read_the_other_tenant_or_delete():
    headers = headers_for("ada", "north")
    assert [row["id"] for row in client.get("/records", headers=headers).json()["records"]] == ["rec-1"]
    assert client.get("/records", headers={**headers, "X-Tenant": "south"}).status_code == 403
    assert client.delete("/records/rec-1", headers=headers).status_code == 403


def test_code_works_once():
    verifier = secrets.token_urlsafe(48)
    code = code_for("ada", verifier)
    assert exchange(code, verifier).status_code == 200
    replay = exchange(code, verifier)
    assert replay.status_code == 401
    assert "already used" in replay.json()["detail"]


def test_wrong_verifier_is_refused():
    code = code_for("ada", secrets.token_urlsafe(48))
    response = exchange(code, secrets.token_urlsafe(48))
    assert response.status_code == 401
    assert "code_verifier" in response.json()["detail"]


def test_redirect_must_match():
    verifier = secrets.token_urlsafe(48)
    assert client.get(
        "/oauth/authorize",
        params={"client_id": "local-console", "redirect_uri": "https://evil.example/cb", "user": "ada", "code_challenge": auth.challenge_for(verifier)},
    ).status_code == 422
    code = code_for("ada", verifier)
    assert exchange(code, verifier, redirect="http://localhost:5173/other").status_code == 401


def test_viewer_reads_but_cannot_create():
    headers = headers_for("linus", "south")
    assert [row["id"] for row in client.get("/records", headers=headers).json()["records"]] == ["rec-2"]
    assert client.post("/records", json={"title": "x"}, headers=headers).status_code == 403


def test_member_creates_in_their_own_tenant():
    headers = headers_for("ada", "north")
    created = client.post("/records", json={"title": "  standup notes "}, headers=headers)
    assert created.status_code == 201
    assert created.json()["tenant"] == "north"
    assert created.json()["title"] == "standup notes"


def test_admin_cannot_delete_another_tenants_record():
    headers = headers_for("grace", "north")
    assert client.delete("/records/rec-2", headers=headers).status_code == 404
    assert client.delete("/records/rec-1", headers=headers).json() == {"deleted": "rec-1"}


def test_audit_is_admin_only_and_tenant_scoped():
    member = headers_for("ada", "north")
    admin = headers_for("grace", "north")
    client.post("/records", json={"title": "from ada"}, headers=member)
    assert client.get("/audit", headers=member).status_code == 403
    events = client.get("/audit", headers=admin).json()["events"]
    assert [(event["actor"], event["action"]) for event in events] == [("ada", "create")]


def test_me_lists_permissions():
    body = client.get("/me", headers=headers_for("grace", "north")).json()
    assert body["permissions"] == ["audit", "create", "delete", "read"]
