from pydantic import BaseModel


class RateLimitDecision(BaseModel):
    """Internal decision returned by the rate limiter to the middleware."""

    allowed: bool
    fail_close: bool = False
