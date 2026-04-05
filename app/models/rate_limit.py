from pydantic import BaseModel


class RateLimitDecision(BaseModel):
    """Data model representing the decision returned by the rate limiter."""

    allowed: bool
    tokens_remaining: int
    retry_after_seconds: float | None = None
    bucket_capacity: int
    fail_open: bool = False  # Safety Flag
