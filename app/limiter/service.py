from pathlib import Path
import time
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.core.settings import settings
from app.models.policy import ResolvedPolicy
from app.models.rate_limit import RateLimitDecision
from app.prometheus.metrics import REDIS_LATENCY_SECONDS, FAIL_OPEN_TOTAL

logger = logging.getLogger(__name__)


class RedisRateLimiter:

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client
        # Load and register the Lua script
        script_path = Path(__file__).with_name("token_bucket.lua")
        script_source = script_path.read_text(encoding="utf-8")
        self._script = self.redis.register_script(script_source)

    def _bucket_key(self, client_id: str) -> str:
        """Construct the Redis key for the client's token bucket."""
        return f"rate_limit:{client_id}"

    @staticmethod
    def _refill_rate_per_second(requests_per_minute: int) -> float:
        """Convert requests per minute to refill rate in tokens per second."""
        return requests_per_minute / 60.0

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

            # Unpack values returned by the Lua script
            allowed_raw, tokens_raw, retry_after_raw = result

            allowed = bool(int(allowed_raw))
            tokens_remaining = int(float(tokens_raw))

            # If the request is not allowed, retry_after_raw will contain the number of seconds until the next token is available
            retry_after_seconds = None if allowed else float(retry_after_raw)

            # Return the rate limit decision
            return RateLimitDecision(
                allowed=allowed,
                tokens_remaining=tokens_remaining,
                retry_after_seconds=retry_after_seconds,
                bucket_capacity=bucket_capacity,
                fail_open=False,
            )

        except (RedisError, RedisTimeoutError, TimeoutError) as e:
            # If Redis is down, catch and log
            logger.critical(
                "Redis unavailable during rate-limit check for client_id=%s. "
                "Failing open. Error=%s",
                policy.client_id,
                e,
            )

            if settings.prometheus_enabled:
                # Increment total requests counter when fail open is true
                FAIL_OPEN_TOTAL.inc()

            # Fail open: allow the request if Redis is unavailable, flip fail_open
            return RateLimitDecision(
                allowed=True,
                tokens_remaining=bucket_capacity,
                retry_after_seconds=None,
                bucket_capacity=bucket_capacity,
                fail_open=True,
            )

    async def close(self) -> None:
        """Close the Redis connection when done."""
        await self.redis.close()
