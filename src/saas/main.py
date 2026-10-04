from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from saas import auth

app = FastAPI(title="Multi-tenant records")
RECORDS = []
AUDIT = []


def seed():
    RECORDS.clear()
    AUDIT.clear()
    auth.CODES.clear()
    RECORDS.extend(
        [
            {"id": "rec-1", "tenant": "north", "title": "north note", "created_by": "grace"},
            {"id": "rec-2", "tenant": "south", "title": "south note", "created_by": "linus"},
        ]
    )


seed()


class TokenRequest(BaseModel):
    grant_type: str
    code: str
    client_id: str
    redirect_uri: str
    code_verifier: str = Field(min_length=43, max_length=128)


class RecordIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


def guarded(action):
    try:
        return action()
    except auth.AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


def record_event(claims, action, record_id):
    AUDIT.append(
        {
            "tenant": claims["tenant"],
            "actor": claims["sub"],
            "action": action,
            "record": record_id,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )


def checked(authorization, tenant, permission):
    def run():
        claims = auth.decode(authorization)
        auth.require(claims, tenant, permission)
        return claims

    return guarded(run)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/oauth/authorize")
def authorize(client_id: str, redirect_uri: str, user: str, code_challenge: str, code_challenge_method: str = "S256", state: str = ""):
    code = guarded(lambda: auth.authorize(client_id, redirect_uri, user, code_challenge, code_challenge_method))
    return {"code": code, "state": state}


@app.post("/oauth/token")
def token(body: TokenRequest):
    encoded = guarded(lambda: auth.exchange(body.grant_type, body.code, body.client_id, body.redirect_uri, body.code_verifier))
    return {"access_token": encoded, "token_type": "bearer", "expires_in": 3600}


@app.get("/me")
def me(authorization: str = Header(default="")):
    claims = guarded(lambda: auth.decode(authorization))
    return {"sub": claims["sub"], "tenant": claims["tenant"], "role": claims["role"], "permissions": sorted(auth.PERMISSIONS[claims["role"]])}


@app.get("/records")
def records(authorization: str = Header(default=""), x_tenant: str = Header(default="")):
    claims = checked(authorization, x_tenant, "read")
    return {"records": [row for row in RECORDS if row["tenant"] == claims["tenant"]]}


@app.post("/records", status_code=201)
def create_record(body: RecordIn, authorization: str = Header(default=""), x_tenant: str = Header(default="")):
    claims = checked(authorization, x_tenant, "create")
    row = {"id": f"rec-{len(RECORDS) + 1}", "tenant": claims["tenant"], "title": body.title.strip(), "created_by": claims["sub"]}
    RECORDS.append(row)
    record_event(claims, "create", row["id"])
    return row


@app.delete("/records/{record_id}")
def delete_record(record_id: str, authorization: str = Header(default=""), x_tenant: str = Header(default="")):
    claims = checked(authorization, x_tenant, "delete")
    for index, row in enumerate(RECORDS):
        if row["id"] == record_id and row["tenant"] == claims["tenant"]:
            RECORDS.pop(index)
            record_event(claims, "delete", record_id)
            return {"deleted": record_id}
    raise HTTPException(status_code=404, detail="record not found")


@app.get("/audit")
def audit(authorization: str = Header(default=""), x_tenant: str = Header(default="")):
    claims = checked(authorization, x_tenant, "audit")
    return {"events": [event for event in AUDIT if event["tenant"] == claims["tenant"]]}
