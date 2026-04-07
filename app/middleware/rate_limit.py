import logging

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from app.core.settings import settings
from app.prometheus.metrics import (
    REQUESTS_TOTAL,
    REQUESTS_ALLOWED_TOTAL,
    REQUESTS_REJECTED_TOTAL,
    REQUESTS_DURING_OUTAGE_TOTAL,
)

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that intercepts incoming requests, enforces rate limits,
    and proxies allowed requests to the protected backend service."""

    async def dispatch(self, request: Request, call_next):
        # Limitr's own operational endpoints bypass rate limiting and proxying
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in settings.excluded_paths):
            return await call_next(request)

        if settings.prometheus_enabled:
            REQUESTS_TOTAL.inc()

        # Extract client identity from request headers
        client_id = request.headers.get(settings.client_id_header)

        if not client_id:
            return JSONResponse(
                status_code=400,
                content={"detail": "Bad request."},
            )

        policy_loader = request.app.state.policy_loader
        rate_limiter = request.app.state.rate_limiter

        policy = policy_loader.get_policy_for_client(client_id)

        if policy is None:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden."},
            )

        decision = await rate_limiter.check_rate_limit(policy)

        if decision.fail_close:
            if settings.prometheus_enabled:
                REQUESTS_REJECTED_TOTAL.inc()
                REQUESTS_DURING_OUTAGE_TOTAL.inc()
            return JSONResponse(
                status_code=503,
                content={"detail": "Service unavailable."},
            )

        if not decision.allowed:
            if settings.prometheus_enabled:
                REQUESTS_REJECTED_TOTAL.inc()
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
            )

        if settings.prometheus_enabled:
            REQUESTS_ALLOWED_TOTAL.inc()

        # Forward the allowed request to the protected backend service
        return await self._proxy_request(request)

    async def _proxy_request(
        self, request: Request
    ) -> StreamingResponse | JSONResponse:
        """Forward the request to the backend and stream the response back."""
        http_client: httpx.AsyncClient = request.app.state.http_client

        # Extract the request body to forward it to the backend
        body = await request.body()

        try:
            # Build the backend request by copying needed components from the original request
            backend_response = await http_client.request(
                method=request.method,  # Extract and copy the HTTP method
                url=str(request.url.path),  # Extract and copy the endpoint
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() != "host"
                },
                params=dict(request.query_params),  # Copy query parameters
                content=body,  # Copy the request body
            )
        except httpx.ConnectError as e:
            logger.error("Backend unreachable: %s", e)
            return JSONResponse(
                status_code=502,
                content={"detail": "Service unavailable."},
            )
        # Copy backend response and send back to the client
        return StreamingResponse(
            content=iter([backend_response.content]),
            status_code=backend_response.status_code,
            headers=dict(backend_response.headers),
        )
