"""
Integration tests for health check API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthAPI:
    """Test health check endpoints."""

    def test_main_health_check(self, client: TestClient):
        """Test main health check endpoint."""
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data

        # Check services status
        services = data["services"]
        expected_services = ["database", "redis", "kafka", "rabbitmq"]
        for service in expected_services:
            assert service in services
            assert services[service] in ["healthy", "unhealthy"]

    def test_database_health_check(self, client: TestClient):
        """Test database-specific health check."""
        response = client.get("/api/v1/health/database")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert data["service"] == "database"
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data

    def test_redis_health_check(self, client: TestClient):
        """Test Redis-specific health check."""
        response = client.get("/api/v1/health/redis")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert data["service"] == "redis"
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data

    def test_readiness_check(self, client: TestClient):
        """Test readiness probe endpoint."""
        response = client.get("/api/v1/health/ready")

        # May be 200 or 503 depending on service availability
        assert response.status_code in [200, 503]
        data = response.json()

        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert "timestamp" in data
        assert "services" in data

        # Check individual service readiness
        services = data["services"]
        expected_services = ["database", "redis", "kafka", "rabbitmq"]
        for service in expected_services:
            assert service in services
            assert isinstance(services[service], bool)

    def test_liveness_check(self, client: TestClient):
        """Test liveness probe endpoint."""
        response = client.get("/api/v1/health/live")

        # Liveness should always be 200 unless the app is completely broken
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "uptime" in data

    def test_legacy_health_redirect(self, client: TestClient):
        """Test legacy health endpoint redirects properly."""
        response = client.get("/health", follow_redirects=False)

        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/api/v1/health"

    def test_health_check_response_structure(self, client: TestClient):
        """Test that health check response follows expected structure."""
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        required_fields = ["status", "timestamp", "service", "version", "environment"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate timestamp format (ISO 8601)
        import datetime
        try:
            datetime.datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid timestamp format")

        # Validate status values
        assert data["status"] in ["healthy", "unhealthy"]

        # Validate environment
        assert data["environment"] in ["development", "testing", "staging", "production"]

    def test_health_check_headers(self, client: TestClient):
        """Test health check response headers."""
        response = client.get("/api/v1/health/")

        # Should have request ID header
        assert "x-request-id" in response.headers

        # Should have content type
        assert response.headers["content-type"] == "application/json"

    def test_concurrent_health_checks(self, client: TestClient):
        """Test multiple concurrent health check requests."""
        import concurrent.futures


        def make_health_request():
            return client.get("/api/v1/health/")

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
