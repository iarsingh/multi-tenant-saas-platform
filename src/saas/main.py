import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

SECRET = os.environ.get("SAAS_SECRET", "dev-only-change-me-32-characters-min")
app = FastAPI(title="Multi-tenant records")
CODES = {"demo-code": {"tenant": "north", "role": "member", "sub": "ada"}}
RECORDS = [{"id": "rec-1", "tenant": "north", "title": "north note"}, {"id": "rec-2", "tenant": "south", "title": "south note"}]


class TokenRequest(BaseModel):
    grant_type: str
    code: str
    client_id: str


def decode(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="bearer token required")
    try:
        return jwt.decode(authorization.removeprefix("Bearer "), SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


@app.get("/oauth/authorize")
def authorize(client_id: str, state: str = ""):
    if client_id != "local-console":
        raise HTTPException(status_code=422, detail="unknown client")
    return {"code": "demo-code", "state": state}


@app.post("/oauth/token")
def token(body: TokenRequest):
    if body.grant_type != "authorization_code" or body.client_id != "local-console":
        raise HTTPException(status_code=422, detail="unsupported grant")
    identity = CODES.get(body.code)
    if identity is None:
        raise HTTPException(status_code=401, detail="unknown code")
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    encoded = jwt.encode({**identity, "exp": expires}, SECRET, algorithm="HS256")
    return {"access_token": encoded, "token_type": "bearer"}


@app.get("/records")
def records(authorization: str = Header(default=""), x_tenant: str = Header(default="")):
    claims = decode(authorization)
    if claims["tenant"] != x_tenant:
        raise HTTPException(status_code=403, detail="token tenant does not match X-Tenant")
    return {"records": [row for row in RECORDS if row["tenant"] == claims["tenant"]]}


@app.delete("/records/{record_id}")
def delete_record(record_id: str, authorization: str = Header(default=""), x_tenant: str = Header(default="")):
    claims = decode(authorization)
    if claims["role"] != "admin":
        raise HTTPException(status_code=403, detail="member cannot delete a record")
    if claims["tenant"] != x_tenant:
        raise HTTPException(status_code=403, detail="token tenant does not match X-Tenant")
    return {"deleted": record_id}
