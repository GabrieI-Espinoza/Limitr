"""Integration tests: middleware + Redis + Lua token bucket end-to-end.

These tests require a running Redis instance at the URL configured in settings.
"""

import pytest


@pytest.mark.asyncio
async def test_allowed_request_proxied(test_client):
    """An allowed request should be forwarded and return a response."""
    response = await test_client.get("/test", headers={"X-API-Key": "test_client_a"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_client_header_returns_400(test_client):
    """A request without the identity header should return 400."""
    response = await test_client.get("/test")
    assert response.status_code == 400
    assert response.json() == {"detail": "Bad request."}


@pytest.mark.asyncio
async def test_unknown_client_returns_403(test_client):
    """A request with an unrecognized client ID should return 403."""
    response = await test_client.get("/test", headers={"X-API-Key": "unknown_client"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden."}


@pytest.mark.asyncio
async def test_quota_exhaustion_returns_429(test_client):
    """After exhausting burst capacity, requests should be rejected with 429."""
    # test_client_b is low_priority with burst_capacity=5
    for _ in range(5):
        response = await test_client.get(
            "/test", headers={"X-API-Key": "test_client_b"}
        )
        assert response.status_code == 200

    # Next request should be rejected
    response = await test_client.get("/test", headers={"X-API-Key": "test_client_b"})
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded."}


@pytest.mark.asyncio
async def test_health_endpoint_bypasses_rate_limiting(test_client):
    """The /health endpoint should work without any headers."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
