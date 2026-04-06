import logging

import httpx
from fastapi import FastAPI

from app.core.settings import settings
from app.limiter.policy_loader import PolicyLoader
from app.limiter.redis_client import create_redis_client
from app.limiter.service import RedisRateLimiter

logger = logging.getLogger(__name__)


async def setup_dependencies(app: FastAPI) -> None:
    """Initializes and injects dependencies into the FastAPI application state."""

    # Load Policies
    policy_loader = PolicyLoader(settings.policy_file_path)
    await policy_loader.load()
    logger.info("Policies loaded from %s", settings.policy_file_path)

    # Initialize Redis client and rate limiter
    redis_client = create_redis_client(settings.redis_url)
    rate_limiter = RedisRateLimiter(redis_client)
    logger.info("Redis connected at %s", settings.redis_url)

    # Initialize HTTP client for proxying requests to the backend service
    http_client = httpx.AsyncClient(base_url=settings.backend_url)

    # Inject dependencies into application state, making them accessible throughout the app
    app.state.policy_loader = policy_loader
    app.state.redis_client = redis_client
    app.state.rate_limiter = rate_limiter
    app.state.http_client = http_client


async def shutdown_dependencies(app: FastAPI) -> None:
    """Cleans up resources and connections during application shutdown."""

    rate_limiter = getattr(app.state, "rate_limiter", None)
    if rate_limiter is not None:
        await rate_limiter.close()

    http_client = getattr(app.state, "http_client", None)
    if http_client is not None:
        await http_client.aclose()
