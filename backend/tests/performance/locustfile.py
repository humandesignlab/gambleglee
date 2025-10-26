"""Locust performance tests for GambleGlee API."""

from locust import HttpUser, task, between


class GambleGleeUser(HttpUser):
    """Simulated user for performance testing."""
    
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Called when a user starts."""
        # Login or setup if needed
        pass

    @task(3)
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/health")

    @task(2)
    def api_health(self):
        """Test API health endpoint."""
        self.client.get("/api/health")

    @task(1)
    def get_public_bets(self):
        """Test getting public bets."""
        self.client.get("/api/v1/bets/public/active")

    @task(1)
    def get_location_info(self):
        """Test location endpoint."""
        self.client.get("/api/v1/location")
