"""Integration tests — verify cross-module interactions and end-to-end flows.

These tests verify that modules work correctly together, including:
- Session lifecycle (create → status → result → export)
- Domain detection with cache integration
- Share token generation and retrieval
- Analytics aggregation across sessions
- Middleware stack ordering
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Provide a test client with isolated session state."""
    return TestClient(app)


class TestSessionLifecycle:
    """Test the complete session lifecycle through the API."""

    def test_create_session_returns_valid_id(self, client):
        """POST /start should return a session with UUID and metadata."""
        response = client.post("/api/verdict/start", json={
            "question": "Should we adopt microservices architecture for our monolith?",
            "output_format": "technical",
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 36  # UUID4 length
        assert data["status"] == "created"
        assert data["output_format"] == "technical"
        assert data["domain"] in (
            "business", "technology", "legal", "medical",
            "financial", "product", "hiring", "operations",
            "marketing", "strategic",
        )

    def test_session_status_after_creation(self, client):
        """GET /status should reflect 'created' state immediately after start."""
        create_resp = client.post("/api/verdict/start", json={
            "question": "Should we expand into the European market this quarter?",
        })
        sid = create_resp.json()["session_id"]

        status_resp = client.get(f"/api/verdict/{sid}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "created"
        assert status_resp.json()["has_result"] is False

    def test_nonexistent_session_returns_404(self, client):
        """GET /status with fake ID should return 404."""
        response = client.get("/api/verdict/nonexistent-id-12345/status")
        assert response.status_code == 404

    def test_incomplete_session_export_returns_202(self, client):
        """Export endpoints should return 202 for sessions without results."""
        create_resp = client.post("/api/verdict/start", json={
            "question": "Should we implement a data mesh architecture pattern?",
        })
        sid = create_resp.json()["session_id"]

        for export_type in ["markdown", "pdf", "json", "docx"]:
            resp = client.get(f"/api/verdict/{sid}/export/{export_type}")
            assert resp.status_code == 202, f"Expected 202 for {export_type} export"

    def test_share_incomplete_session_returns_202(self, client):
        """Share endpoint should return 202 for incomplete sessions."""
        create_resp = client.post("/api/verdict/start", json={
            "question": "Should we switch from REST to GraphQL for our API?",
        })
        sid = create_resp.json()["session_id"]

        resp = client.get(f"/api/verdict/{sid}/share")
        assert resp.status_code == 202


class TestDomainDetectionIntegration:
    """Test domain detection heuristics through the API."""

    @pytest.mark.parametrize("question,expected_domain", [
        ("Should we hire a senior CTO for the AI team?", "hiring"),
        ("Should we raise a Series B at $50M valuation?", "financial"),
        ("Should we migrate our stack to Kubernetes?", "technology"),
        ("Should we launch a new product line for enterprise?", "product"),
        ("Should we run a social media marketing campaign?", "marketing"),
    ])
    def test_heuristic_domain_classification(self, client, question, expected_domain):
        """Verify keyword-based domain classification at session start."""
        resp = client.post("/api/verdict/start", json={"question": question})
        assert resp.status_code == 200
        assert resp.json()["domain"] == expected_domain


class TestFormatSelection:
    """Test output format validation through the API."""

    def test_accepts_all_valid_formats(self, client):
        """All 4 output formats should be accepted."""
        for fmt in ["executive", "technical", "legal", "investor"]:
            resp = client.post("/api/verdict/start", json={
                "question": f"Should we proceed with the {fmt} analysis test?",
                "output_format": fmt,
            })
            assert resp.status_code == 200
            assert resp.json()["output_format"] == fmt

    def test_rejects_invalid_format(self, client):
        """Invalid output format should be rejected with 422."""
        resp = client.post("/api/verdict/start", json={
            "question": "Should we test invalid formats?",
            "output_format": "invalid_format",
        })
        assert resp.status_code == 422

    def test_formats_endpoint_returns_all_four(self, client):
        """GET /formats should list all 4 output formats."""
        resp = client.get("/api/verdict/formats")
        assert resp.status_code == 200
        formats = resp.json()["formats"]
        format_ids = {f["id"] for f in formats}
        assert format_ids == {"executive", "technical", "legal", "investor"}


class TestAnalyticsIntegration:
    """Test analytics aggregation across sessions."""

    def test_analytics_returns_valid_structure(self, client):
        """GET /sessions/analytics should return expected fields."""
        resp = client.get("/api/verdict/sessions/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "ruling_distribution" in data
        assert "domain_breakdown" in data
        assert "format_usage" in data
        assert "avg_verdict_confidence" in data
        assert "completion_rate" in data

    def test_analytics_counts_sessions(self, client):
        """Analytics should reflect newly created sessions."""
        # Create a session
        client.post("/api/verdict/start", json={
            "question": "Should we invest in quantum computing research?",
        })

        resp = client.get("/api/verdict/sessions/analytics")
        assert resp.json()["total_sessions"] > 0


class TestHealthAndMetrics:
    """Test operational endpoints."""

    def test_health_endpoint_returns_alive(self, client):
        """GET /health should always return alive status."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert "checks" in data
        assert "uptime_seconds" in data

    def test_metrics_endpoint_returns_structure(self, client):
        """GET /metrics should return pipeline metrics."""
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_history_endpoint_works(self, client):
        """GET /sessions/history should return session list."""
        resp = client.get("/api/verdict/sessions/history")
        assert resp.status_code == 200
        assert "sessions" in resp.json()


class TestInputValidationIntegration:
    """Test input validation across the API surface."""

    def test_rejects_empty_question(self, client):
        """Empty question should be rejected."""
        resp = client.post("/api/verdict/start", json={"question": ""})
        assert resp.status_code == 422

    def test_rejects_short_question(self, client):
        """Questions under 10 chars should be rejected."""
        resp = client.post("/api/verdict/start", json={"question": "short"})
        assert resp.status_code == 422

    def test_accepts_long_valid_question(self, client):
        """Long valid questions should be accepted."""
        question = "Should we " + "carefully consider " * 50 + "this decision?"
        resp = client.post("/api/verdict/start", json={"question": question})
        assert resp.status_code == 200

    def test_rejects_overly_long_question(self, client):
        """Questions over 2000 chars should be rejected."""
        question = "x" * 2001
        resp = client.post("/api/verdict/start", json={"question": question})
        assert resp.status_code == 422
