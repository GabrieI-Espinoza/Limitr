from prometheus_client import Counter, Histogram, Gauge

LIMITR_DOWN = Gauge(
    "limitr_down",
    "Indicates whether Limitr is currently down (1) or up (0)",
)

LIMITR_OUTAGE_SECONDS_TOTAL = Counter(
    "limitr_outage_seconds_total",
    "Total number of seconds Limitr has been down",
)

REQUESTS_DURING_OUTAGE_TOTAL = Counter(
    "limitr_requests_during_outage_total",
    "Total number of requests received while Limitr is down",
)

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
