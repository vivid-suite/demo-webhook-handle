# demo-webhook-handle

File: ops/README.md (project root README)
Purpose: FastAPI demo service for webhook handling with HMAC signature stub.
Why: Powers VividSuite marketing demos via Oracle subdomain behind NGINX+TLS.
Related: [app/main.py](app/main.py), [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), [ops/nginx/webhook-handle.conf](ops/nginx/webhook-handle.conf)

## Quick start (Docker Compose)

1) Copy env template and adjust values:

```bash
cp .env.example .env
```

2) Bring up the service (binds to 127.0.0.1:8004):

```bash
docker compose up -d --build
```

3) Smoke tests:

```bash
curl -s http://127.0.0.1:8004/healthz | jq .

# GET demo payload
curl -s http://127.0.0.1:8004/demo/example | jq .

# POST with signature (replace SECRET)
SECRET="changeme"
BODY='{"hello":"world","n":1}'
SIG="sha256=$(python - <<PY
import hmac,hashlib,sys
secret=sys.argv[1].encode(); body=sys.argv[2].encode()
print(hmac.new(secret, body, hashlib.sha256).hexdigest())
PY "$SECRET" "$BODY")"

curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY" \
  http://127.0.0.1:8004/demo/example | jq .
```

## CORS

- ALLOWED_ORIGINS controls explicit origins (comma-separated).
- ALLOW_NETLIFY_WILDCARD=true enables `https://*.netlify.app` previews.
- Default includes `http://localhost:4321` and `https://vividsuite.io`.

## NGINX + TLS (Oracle VM)

- Place this vhost: [ops/nginx/webhook-handle.conf](ops/nginx/webhook-handle.conf)
- Obtain certs via certbot using `/.well-known/acme-challenge/` on port 80.
- NGINX proxies HTTPS traffic to `127.0.0.1:8004` (container stays private).

## Notes

- This repo contains synthetic demo endpoints only; no real data.
- Signature header expected: `X-Signature: sha256=<hex>` where `<hex>` is HMAC-SHA256 of the canonical JSON body using `WEBHOOK_SECRET`.

## License

MIT
