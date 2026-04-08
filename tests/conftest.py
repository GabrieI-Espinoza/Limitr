import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.settings import settings
from app.limiter.policy_loader import PolicyLoader
from app.limiter.redis_client import create_redis_client
from app.limiter.service import RedisRateLimiter


async def _mock_backend_handler(request: httpx.Request) -> httpx.Response:
    """Simulates the protected backend service for integration tests."""
    return httpx.Response(
        200,
        json={
            "service": "mock-backend",
            "method": request.method,
            "path": str(request.url.path),
        },
    )


@pytest_asyncio.fixture
async def redis_client():
    """Provide a real Redis client and flush test data between tests."""
    client = create_redis_client(settings.redis_url)
    # Clean rate_limit keys before each test
    async for key in client.scan_iter("rate_limit:*"):
        await client.delete(key)
    yield client
    # Clean up after test
    async for key in client.scan_iter("rate_limit:*"):
        await client.delete(key)
    await client.aclose()


@pytest_asyncio.fixture
async def test_client(redis_client, tmp_path):
    """Provide a fully wired test client with real Redis and a mock backend."""
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
tiers:
  enterprise:
    requests_per_minute: 120
    burst_capacity: 20
  free:
    requests_per_minute: 6
    burst_capacity: 3

clients:
  test_client_a: enterprise
  test_client_b: free
  test_client_c: free
"""
    )

    policy_loader = PolicyLoader(str(policy_file))
    await policy_loader.load()
    rate_limiter = RedisRateLimiter(redis_client)

    app.state.policy_loader = policy_loader
    app.state.redis_client = redis_client
    app.state.rate_limiter = rate_limiter

    # Backend used by the app during proxying.
    # MockTransport intercepts proxied outbound requests and returns a fake backend response.
    app.state.http_client = AsyncClient(
        transport=httpx.MockTransport(_mock_backend_handler),
        base_url="http://mock-backend",
    )

    # Test client sending the initial request into the app for validation.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client

    await rate_limiter.close()
    await app.state.http_client.aclose()


@pytest.fixture
def rate_limiter(test_client):
    """Provide direct access to the rate limiter for fault injection tests."""
    return app.state.rate_limiter
