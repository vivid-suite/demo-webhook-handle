# File: app/main.py
# Purpose: FastAPI demo service for webhook handling; exposes /healthz and /demo/example with HMAC-signature verification stub.
# Why: Provides a safe, synthetic demo backend for the marketing site to call; mirrors typical webhook verification flows.
# Related: Dockerfile, docker-compose.yml, ops/nginx/webhook-handle.conf

import os
import json
import hmac
import hashlib
import time
from typing import Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


def env_bool(name: str, default: str = "false") -> bool:
    val = os.getenv(name, default).strip().lower()
    return val in {"1", "true", "yes", "on"}


def parse_csv_env(name: str, default: str = ""):
    raw = os.getenv(name, default)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts


PORT = int(os.getenv("PORT", "8004"))
ALLOWED_ORIGINS = parse_csv_env(
    "ALLOWED_ORIGINS",
    "http://localhost:4321,https://vividsuite.io",
)
ALLOW_NETLIFY_WILDCARD = env_bool("ALLOW_NETLIFY_WILDCARD", "true")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

app = FastAPI(title="demo-webhook-handle", version="0.1.0")

# CORS — allow specific origins plus optional Netlify wildcard
cors_kwargs = dict(
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"] ,
    max_age=600,
)
if ALLOW_NETLIFY_WILDCARD:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=r"^https://.*\.netlify\.app$",
        **cors_kwargs,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        **cors_kwargs,
    )


def _normalized_body_for_hmac(raw: bytes) -> bytes:
    """Return the bytes to sign. For JSON, we try to canonicalize the payload.

    This helps avoid false negatives from whitespace/ordering differences.
    If parsing fails, we fall back to the raw body as-is.
    """
    try:
        data = json.loads(raw.decode("utf-8"))
        canonical = json.dumps(data, separators=(",", ":"), sort_keys=True)
        return canonical.encode("utf-8")
    except Exception:
        return raw


def compute_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, header_signature: str) -> Tuple[Optional[bool], Optional[str]]:
    """Verify an incoming signature header against computed digest.

    Returns (is_valid, expected_signature). If header or secret missing, returns (None, expected).
    """
    if not secret:
        expected = compute_signature("demo-secret", _normalized_body_for_hmac(body))
        return None, expected

    expected = compute_signature(secret, _normalized_body_for_hmac(body))

    supplied = (header_signature or "").strip()
    if supplied.lower().startswith("sha256="):
        supplied = supplied.split("=", 1)[1]
    expected_hex = expected.split("=", 1)[1]

    is_valid = hmac.compare_digest(supplied, expected_hex)
    return is_valid, expected


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "service": "webhook-handle",
        "time": int(time.time()),
    }


@app.get("/demo/example")
async def demo_example_get():
    """Return a synthetic webhook-style payload and example signature.

    The marketing site can call this with GET to retrieve a stable, demo-safe response.
    """
    sample_event = {
        "event": "example.webhook",
        "id": "evt_demo_123",
        "received_at": int(time.time()),
        "data": {
            "object": {
                "id": "obj_demo_123",
                "amount": 1999,
                "currency": "usd",
                "tags": ["demo", "webhook", "handle"],
            }
        },
    }

    example_sig = None
    if WEBHOOK_SECRET:
        body = json.dumps(sample_event, separators=(",", ":"), sort_keys=True).encode("utf-8")
        example_sig = compute_signature(WEBHOOK_SECRET, body)

    return {
        "service": "webhook-handle",
        "example": sample_event,
        "how_to_test": "POST JSON to /demo/example with header 'X-Signature: sha256=...' computed using your WEBHOOK_SECRET.",
        "signature_example": example_sig,
    }


@app.post("/demo/example")
async def demo_example_post(request: Request):
    """Accept a JSON payload and attempt to verify HMAC signature if provided.

    Header: X-Signature = sha256=<hex>
    Env: WEBHOOK_SECRET="""
    raw = await request.body()
    supplied_sig = request.headers.get("X-Signature") or request.headers.get("x-signature") or ""

    is_valid, expected = verify_signature(WEBHOOK_SECRET, raw, supplied_sig)

    parsed = None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        pass

    return {
        "service": "webhook-handle",
        "received_bytes": len(raw),
        "received": parsed,
        "signature_valid": is_valid,   # true/false/None
        "expected_signature": expected, # what server computed
        "note": (
            "signature check skipped (missing secret or header)"
            if is_valid is None else "signature compared"
        ),
        "time": int(time.time()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=False)
