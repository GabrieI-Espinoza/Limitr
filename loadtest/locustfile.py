"""Locust load test for Limitr.

Simulates concurrent traffic from multiple clients across priority tiers.
Run against the Nginx load balancer to validate distributed rate limiting.

Usage:
    locust -f loadtest/locustfile.py --host http://localhost
"""

from locust import HttpUser, task, between, tag


class Tier1Client(HttpUser):
    """High-priority client (1000 req/min)."""

    weight = 3
    wait_time = between(0.05, 0.1)

    @tag("steady", "tier1")
    @task
    def send_request(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_a"},
            name="/api/data [tier1]",
        )


class Tier2Client(HttpUser):
    """Medium-priority client (100 req/min)."""

    weight = 5
    wait_time = between(0.3, 0.6)

    @tag("steady", "tier2")
    @task
    def send_request(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_d"},
            name="/api/data [tier2]",
        )


class Tier3Client(HttpUser):
    """Low-priority client (10 req/min)."""

    weight = 2
    wait_time = between(1, 2)

    @tag("steady", "tier3")
    @task
    def send_request(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_j"},
            name="/api/data [tier3]",
        )


class BurstClient(HttpUser):
    """Simulates short bursts of traffic to test token bucket burst handling."""

    weight = 1
    wait_time = between(0.01, 0.02)

    @tag("burst")
    @task
    def send_burst(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_e"},
            name="/api/data [burst]",
        )
