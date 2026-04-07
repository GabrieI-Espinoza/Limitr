"""Fault injection and resilience tests.

Simulates Redis failures to verify fail-closed behavior and clean recovery.
These tests require a running Redis instance at the URL configured in settings.
"""

import pytest
from unittest.mock import AsyncMock, patch

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError


@pytest.mark.asyncio
async def test_redis_down_returns_503(test_client, rate_limiter):
    """When Redis is unavailable, requests should be rejected with 503."""
    with patch.object(
        rate_limiter,
        "_script",
        new_callable=AsyncMock,
        side_effect=RedisConnectionError("Connection refused"),
    ):
        response = await test_client.get(
            "/test", headers={"X-API-Key": "test_client_a"}
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable."}


@pytest.mark.asyncio
async def test_503_response_is_generic(test_client, rate_limiter):
    """Fail-closed responses must not leak internal details."""
    with patch.object(
        rate_limiter,
        "_script",
        new_callable=AsyncMock,
        side_effect=RedisConnectionError("Connection refused"),
    ):
        response = await test_client.get(
            "/test", headers={"X-API-Key": "test_client_a"}
        )

    assert response.status_code == 503
    body = response.json()
    assert "redis" not in body.get("detail", "").lower()
    assert "connection" not in body.get("detail", "").lower()


@pytest.mark.asyncio
async def test_recovery_after_redis_outage(test_client, rate_limiter):
    """After Redis recovers, requests should be allowed again."""
    with patch.object(
        rate_limiter,
        "_script",
        new_callable=AsyncMock,
        side_effect=RedisConnectionError("Connection refused"),
    ):
        response = await test_client.get(
            "/test", headers={"X-API-Key": "test_client_a"}
        )
        assert response.status_code == 503

    # Redis is back — real Redis handles the request
    response = await test_client.get("/test", headers={"X-API-Key": "test_client_a"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_redis_timeout_triggers_fail_closed(test_client, rate_limiter):
    """A Redis timeout should also trigger fail-closed behavior."""
    with patch.object(
        rate_limiter,
        "_script",
        new_callable=AsyncMock,
        side_effect=RedisTimeoutError("Timed out"),
    ):
        response = await test_client.get(
            "/test", headers={"X-API-Key": "test_client_a"}
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_outage_metrics_recorded(test_client, rate_limiter):
    """Outage-related metrics should update during and after an outage."""
    from app.prometheus.metrics import LIMITR_DOWN, REQUESTS_DURING_OUTAGE_TOTAL

    rate_limiter._is_down = False
    rate_limiter._down_since = None
    LIMITR_DOWN.set(0)
    before = REQUESTS_DURING_OUTAGE_TOTAL._value.get()

    with patch.object(
        rate_limiter,
        "_script",
        new_callable=AsyncMock,
        side_effect=RedisConnectionError("Connection refused"),
    ):
        await test_client.get("/test", headers={"X-API-Key": "test_client_a"})

    assert LIMITR_DOWN._value.get() == 1
    assert REQUESTS_DURING_OUTAGE_TOTAL._value.get() - before == 1

    # Recover and verify gauge resets
    await test_client.get("/test", headers={"X-API-Key": "test_client_a"})
    assert LIMITR_DOWN._value.get() == 0
