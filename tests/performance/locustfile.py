from __future__ import annotations

from locust import HttpUser, between, task


class FraudApiUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def dashboard_stats(self):
        self.client.get("/api/v1/dashboard/stats")

    @task(1)
    def auth_login_flow(self):
        email = "load-user@test.com"
        password = "Load@12345"
        self.client.post("/api/v1/auth/register", json={"email": email, "full_name": "Load User", "password": password})
        self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
