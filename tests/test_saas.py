from fastapi.testclient import TestClient

from saas.main import app

client = TestClient(app)


def member_token():
    code = client.get("/oauth/authorize", params={"client_id": "local-console", "state": "s"}).json()["code"]
    return client.post("/oauth/token", json={"grant_type": "authorization_code", "code": code, "client_id": "local-console"}).json()["access_token"]


def test_tenant_cannot_read_the_other_tenant_or_delete():
    token = member_token()
    headers = {"Authorization": f"Bearer {token}", "X-Tenant": "north"}
    body = client.get("/records", headers=headers).json()
    assert [row["id"] for row in body["records"]] == ["rec-1"]
    leaked = client.get("/records", headers={"Authorization": f"Bearer {token}", "X-Tenant": "south"})
    assert leaked.status_code == 403
    assert client.delete("/records/rec-1", headers=headers).status_code == 403
