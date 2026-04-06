from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.settings import settings
from app.prometheus.metrics import (
    REQUESTS_TOTAL,
    REQUESTS_ALLOWED_TOTAL,
    REQUESTS_REJECTED_TOTAL,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that intercepts all incoming requests and applies rate limiting."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude all the following paths from rate limiting
        if request.url.path in settings.excluded_paths:
            return await call_next(request)

        if settings.prometheus_enabled:
            # Increment total requests counter
            REQUESTS_TOTAL.inc()

        # Extract client_id from the specified header
        client_id = request.headers.get(settings.client_id_header)

        # If client did not provide the required header, return a 400 Bad Request response
        if not client_id:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": f"Missing required header: {settings.client_id_header}"
                },
            )

        # Retrive the policy loader and rate limiter services from the application state
        policy_loader = request.app.state.policy_loader
        rate_limiter = request.app.state.rate_limiter

        # Extract the rate limit policy for the given client_id
        policy = policy_loader.get_policy_for_client(client_id)

        # If policy is not found for the client_id, return a 403 Forbidden response
        if policy is None:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Unknown client_id: {client_id}"},
            )

        # Wait for token bucket algorithm to check if the request is allowed under the current policy
        decision = await rate_limiter.check_rate_limit(policy)

        # If client has exceeded the rate limit, return a 429 Too Many Requests
        if not decision.allowed:
            if settings.prometheus_enabled:
                # Increment rejected requests counter
                REQUESTS_REJECTED_TOTAL.inc()
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(int(decision.retry_after_seconds or 0)),
                    "X-RateLimit-Limit": str(decision.bucket_capacity),
                    "X-RateLimit-Remaining": str(decision.tokens_remaining),
                },
            )

        if settings.prometheus_enabled:
            # Increment allowed requests counter
            REQUESTS_ALLOWED_TOTAL.inc()

        response = await call_next(request)

        # Add bucket capacity and remaining tokens to the response
        response.headers["X-RateLimit-Limit"] = str(decision.bucket_capacity)
        response.headers["X-RateLimit-Remaining"] = str(decision.tokens_remaining)

        return response
