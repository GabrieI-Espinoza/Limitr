from fastapi import FastAPI
from app.core.settings import settings
from app.limiter.policy_loader import PolicyLoader
from app.limiter.redis_client import create_redis_client
from app.limiter.service import RedisRateLimiter


async def setup_dependencies(app: FastAPI) -> None:
    """Initializes and injects dependencies into the FastAPI application state."""

    # Load policies
    policy_loader = PolicyLoader(settings.policy_file_path)
    await policy_loader.load()

    # Establish connection pool to Redis
    redis_client = create_redis_client(settings.redis_url)
    # Initialize the rate limiter service
    rate_limiter = RedisRateLimiter(redis_client)

    # Inject dependencies into the application state
    app.state.policy_loader = policy_loader
    app.state.redis_client = redis_client
    app.state.rate_limiter = rate_limiter


async def shutdown_dependencies(app: FastAPI) -> None:
    """Cleans up resources and connections during application shutdown."""

    # Retrieve the rate limiter from the application state
    rate_limiter = getattr(app.state, "rate_limiter", None)

    # Close the Redis connection pool if it exists
    if rate_limiter is not None:
        await rate_limiter.close()
