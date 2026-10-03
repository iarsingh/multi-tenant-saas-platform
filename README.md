# Multi-tenant SaaS platform

Level: Intermediate+

Skills: React, FastAPI, tenant isolation, OAuth, RBAC

A local authorization-code exchange issues a JWT for tenant `north` and role `member`. `GET /records` returns only that tenant, and only when `X-Tenant` matches the token. A member who calls `DELETE` is refused.

This is not a Google login. The client id is `local-console` and the demo code is fixed so the test can run without a browser. Redis is not required for this path. The record list is the stand-in for the tenant database.

```bash
pip install -r requirements.txt
pytest -q
```

