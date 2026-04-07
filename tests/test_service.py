"""Unit tests for rate limiter service logic: bucket keys, refill math, outage tracking."""

from unittest.mock import patch
from app.limiter.service import RedisRateLimiter


class TestBucketKey:
    def test_key_format(self):
        """Redis key should follow rate_limit:{client_id} pattern."""
        limiter = RedisRateLimiter.__new__(RedisRateLimiter)
        assert limiter._bucket_key("client_a") == "rate_limit:client_a"


class TestRefillRate:
    def test_refill_rate_conversion(self):
        """requests_per_minute should convert to tokens/sec correctly."""
        rate = RedisRateLimiter._refill_rate_per_second(1000)
        assert abs(rate - 1000 / 60.0) < 1e-9


class TestOutageTracking:
    def _make_limiter(self):
        """Create a limiter instance without connecting to Redis."""
        limiter = RedisRateLimiter.__new__(RedisRateLimiter)
        limiter._is_down = False
        limiter._down_since = None
        return limiter

    @patch("app.limiter.service.settings")
    def test_mark_down_sets_state(self, mock_settings):
        mock_settings.prometheus_enabled = False
        limiter = self._make_limiter()

        limiter._mark_down()

        assert limiter._is_down is True
        assert limiter._down_since is not None

    @patch("app.limiter.service.settings")
    def test_mark_back_up_resets_state(self, mock_settings):
        mock_settings.prometheus_enabled = False
        limiter = self._make_limiter()

        limiter._mark_down()
        limiter._mark_back_up()

        assert limiter._is_down is False
        assert limiter._down_since is None

    @patch("app.limiter.service.settings")
    def test_mark_back_up_noop_when_already_up(self, mock_settings):
        mock_settings.prometheus_enabled = False
        limiter = self._make_limiter()

        limiter._mark_back_up()
        assert limiter._is_down is False
