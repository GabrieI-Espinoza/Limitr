"""Locust load test for Limitr.

Simulates concurrent traffic from multiple clients across priority tiers.
Run against the Nginx load balancer to validate distributed rate limiting.

Usage:
    locust -f loadtest/locustfile.py --host http://localhost
"""

from locust import HttpUser, task, between, tag


class EnterpriseClient(HttpUser):
    """Enterprise client (120 req/min, burst 20)."""

    weight = 2
    wait_time = between(0.3, 0.7)

    @tag("steady", "enterprise")
    @task
    def send_request(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_a"},
            name="/api/data [enterprise]",
        )


class StandardClient(HttpUser):
    """Standard client (30 req/min, burst 10)."""

    weight = 4
    wait_time = between(1, 3)

    @tag("steady", "standard")
    @task
    def send_request(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_c"},
            name="/api/data [standard]",
        )


class FreeClient(HttpUser):
    """Free tier client (6 req/min, burst 3)."""

    weight = 3
    wait_time = between(3, 6)

    @tag("steady", "free")
    @task
    def send_request(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_f"},
            name="/api/data [free]",
        )


class BurstClient(HttpUser):
    """Simulates a client sending a rapid burst to test bucket drain."""

    weight = 1
    wait_time = between(0.05, 0.1)

    @tag("burst")
    @task
    def send_burst(self):
        self.client.get(
            "/api/data",
            headers={"X-API-Key": "client_d"},
            name="/api/data [burst]",
        )
