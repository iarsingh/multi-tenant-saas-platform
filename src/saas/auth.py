import base64
import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt

SECRET = os.environ.get("SAAS_SECRET", "dev-only-change-me-32-characters-min")
CLIENT_ID = "local-console"
REDIRECT_URI = "http://localhost:5173/callback"
CODE_SECONDS = 300
USERS = {
    "ada": {"tenant": "north", "role": "member"},
    "grace": {"tenant": "north", "role": "admin"},
    "linus": {"tenant": "south", "role": "viewer"},
}
PERMISSIONS = {
    "viewer": {"read"},
    "member": {"read", "create"},
    "admin": {"read", "create", "delete", "audit"},
}
CODES = {}


class AuthError(Exception):
    def __init__(self, message, status=401):
        super().__init__(message)
        self.status = status


def challenge_for(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorize(client_id, redirect_uri, user, code_challenge, method="S256"):
    if client_id != CLIENT_ID:
        raise AuthError("unknown client", 422)
    if redirect_uri != REDIRECT_URI:
        raise AuthError("redirect_uri is not registered", 422)
    if user not in USERS:
        raise AuthError("unknown user", 422)
    if method != "S256" or not code_challenge:
        raise AuthError("PKCE with S256 is required", 422)
    code = secrets.token_urlsafe(24)
    CODES[code] = {"user": user, "challenge": code_challenge, "redirect_uri": redirect_uri, "expires": time.time() + CODE_SECONDS}
    return code


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


def issue(claims, hours=1):
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    return jwt.encode({**claims, "exp": expires}, SECRET, algorithm="HS256")


def decode(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("bearer token required")
    try:
        return jwt.decode(authorization.removeprefix("Bearer "), SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AuthError("invalid token") from exc


def require(claims, tenant_header, permission):
    if claims["tenant"] != tenant_header:
        raise AuthError("token tenant does not match X-Tenant", 403)
    if permission not in PERMISSIONS.get(claims["role"], set()):
        raise AuthError(f"{claims['role']} cannot {permission}", 403)
