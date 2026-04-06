from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter(
    "limitr_requests_total",
    "Total number of requests seen by the middleware",
)

REQUESTS_ALLOWED_TOTAL = Counter(
    "limitr_requests_allowed_total",
    "Total number of requests allowed by the rate limiter",
)

REQUESTS_REJECTED_TOTAL = Counter(
    "limitr_requests_rejected_total",
    "Total number of requests rejected by the rate limiter",
)

REDIS_LATENCY_SECONDS = Histogram(
    "limitr_redis_latency_seconds",
    "Latency of Redis rate-limit checks",
)

FAIL_OPEN_TOTAL = Counter(
    "limitr_fail_open_total",
    "Total number of fail-open events when Redis is unavailable",
)
