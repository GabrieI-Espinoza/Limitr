# Limitr

A distributed rate-limiting reverse proxy built with FastAPI and Redis.

Limitr sits between clients and a backend service, enforcing per-client rate limits using a token bucket algorithm. Multiple instances share state through Redis, making rate limits consistent across a load-balanced deployment.

## Architecture

```
                        +----> Limitr-1 ---+
                        |                  |
Client ----> Nginx (LB)-+                  +----> Backend
                        |                  |
                        +----> Limitr-2 ---+
                                 |
                               Redis
                          (shared state)
```

- Requests identified by `X-API-Key` header and matched to a rate limit tier
- Token bucket algorithm runs atomically in Redis via Lua script
- **Fail-closed** design -- all traffic is rejected if Redis is unavailable
- Prometheus metrics exposed at `/metrics`

## Rate Limit Tiers

Configured in [`config/policies.yaml`](config/policies.yaml):

| Tier | Requests/min | Burst |
|------|-------------|-------|
| Enterprise | 120 | 20 |
| Standard | 30 | 10 |
| Free | 6 | 3 |

## Quick Start

**Docker (recommended)**

```bash
docker compose up -d
curl -H "X-API-Key: client_a" http://localhost/api/data
```

**Local development**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker run -d --name redis-limitr -p 6379:6379 redis:8
uvicorn app.main:app --reload
```

## Configuration

All settings are overridden via environment variables with the `LIMITR_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `LIMITR_REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `LIMITR_BACKEND_URL` | `http://localhost:8080` | Upstream service to proxy to |
| `LIMITR_CLIENT_ID_HEADER` | `X-API-Key` | Client identity header |
| `LIMITR_LOG_LEVEL` | `INFO` | Logging verbosity |

## Testing

```bash
# Requires Redis on localhost:6379
.venv/bin/python -m pytest tests/ -v
```

22 tests across unit, integration, and fault injection suites. CI runs automatically via GitHub Actions on push/PR to main.

## Load Testing

```bash
docker compose up -d
locust -f loadtest/locustfile.py --host http://localhost
```

Opens a web UI at `http://localhost:8089` to simulate concurrent traffic across all tiers.