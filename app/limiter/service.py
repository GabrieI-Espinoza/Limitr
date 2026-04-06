from pathlib import Path
import time
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.core.settings import settings
from app.models.policy import ResolvedPolicy
from app.models.rate_limit import RateLimitDecision
from app.prometheus.metrics import (
    REDIS_LATENCY_SECONDS,
    LIMITR_DOWN,
    LIMITR_OUTAGE_SECONDS_TOTAL,
)

logger = logging.getLogger(__name__)


class RedisRateLimiter:

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client
        # Load and register the Lua script
        script_path = Path(__file__).with_name("token_bucket.lua")
        script_source = script_path.read_text(encoding="utf-8")
        self._script = self.redis.register_script(script_source)

        # Helps track if service is down
        self._is_down = False
        # How long service has been down
        self._down_since: float | None = None

        if settings.prometheus_enabled:
            # Initialize tracker to status: UP
            LIMITR_DOWN.set(0)

    def _bucket_key(self, client_id: str) -> str:
        """Construct the Redis key for the client's token bucket."""
        return f"rate_limit:{client_id}"

    @staticmethod
    def _refill_rate_per_second(requests_per_minute: int) -> float:
        """Convert requests per minute to refill rate in tokens per second."""
        return requests_per_minute / 60.0

    def _mark_down(self) -> None:
        """Keeps track of service being down"""
        if not self._is_down:
            self._is_down = True
            self._down_since = time.time()

            if settings.prometheus_enabled:
                # Update tracker to status: DOWN
                LIMITR_DOWN.set(1)

    def _mark_back_up(self) -> None:
        """Keeps tracks when service is back up"""
        if self._is_down:
            now = time.time()
            outage_duration = 0.0

            if self._down_since is not None:
                outage_duration = max(0.0, now - self._down_since)
                if settings.prometheus_enabled:
                    LIMITR_OUTAGE_SECONDS_TOTAL.inc(outage_duration)

            if settings.prometheus_enabled:
                # Update tracker to status: UP
                LIMITR_DOWN.set(0)

            logger.info("Redis recovered after %.1fs outage", outage_duration)

            # Reset status
            self._is_down = False
            self._down_since = None

    async def check_rate_limit(self, policy: ResolvedPolicy) -> RateLimitDecision:
        # Construct the Redis key for the client's token bucket
        key = self._bucket_key(policy.client_id)
        # Extract bucket capacity and refill rate from the policy
        bucket_capacity = policy.burst_capacity
        refill_rate_per_sec = self._refill_rate_per_second(policy.requests_per_minute)

        try:
            # Get the current time to measure Redis latency
            start = time.perf_counter()

            # Execute the Lua script with the necessary key and arguments, for the token bucket algorithm
            result = await self._script(
                keys=[key], args=[bucket_capacity, refill_rate_per_sec]
            )

            # Calulate elapsed time
            elapsed = time.perf_counter() - start
            if settings.prometheus_enabled:
                # Log the latency of the Redis call to Prometheus
                REDIS_LATENCY_SECONDS.observe(elapsed)

            # If redis was down, means redis is back up, update status
            self._mark_back_up()

            allowed = bool(int(result[0]))

            return RateLimitDecision(allowed=allowed)

        except (RedisError, RedisTimeoutError, TimeoutError) as e:
            # If Redis is down, catch and log
            logger.critical(
                "Redis unavailable during rate-limit check for client_id=%s. "
                "Failing closed. Error=%s",
                policy.client_id,
                e,
            )

            # Upon first failure update status, all continuous requests just keeps same status: DOWN
            self._mark_down()

            return RateLimitDecision(allowed=False, fail_close=True)

    async def close(self) -> None:
        """Close the Redis connection when done."""
        await self.redis.aclose()
