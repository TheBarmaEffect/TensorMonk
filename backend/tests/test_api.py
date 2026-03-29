"""Tests for the FastAPI routes — verifying API contract, response shapes, and input validation."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthCheck:
    def test_health_returns_alive(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert "version" in data


class TestStartSession:
    def test_start_returns_session(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we pivot to B2B?",
            "output_format": "executive",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["status"] == "created"
        assert data["output_format"] == "executive"
        assert "domain" in data

    def test_start_detects_hiring_domain(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we hire a CTO for our startup?",
        })
        data = resp.json()
        assert data["domain"] == "hiring"

    def test_start_detects_financial_domain(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we raise a Series A at $15M valuation?",
        })
        data = resp.json()
        assert data["domain"] == "financial"


class TestInputValidation:
    """Verify Pydantic field validators reject malformed input."""

    def test_rejects_empty_question(self):
        resp = client.post("/api/verdict/start", json={"question": ""})
        assert resp.status_code == 422

    def test_rejects_short_question(self):
        resp = client.post("/api/verdict/start", json={"question": "hi"})
        assert resp.status_code == 422

    def test_rejects_whitespace_only(self):
        resp = client.post("/api/verdict/start", json={"question": "         "})
        assert resp.status_code == 422

    def test_rejects_too_long_question(self):
        resp = client.post("/api/verdict/start", json={"question": "x" * 2001})
        assert resp.status_code == 422

    def test_rejects_too_long_context(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we pivot to enterprise B2B?",
            "context": "x" * 5001,
        })
        assert resp.status_code == 422

    def test_rejects_invalid_output_format(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we pivot to enterprise B2B?",
            "output_format": "invalid_format",
        })
        assert resp.status_code == 422

    def test_accepts_valid_question(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we pivot to enterprise B2B SaaS?",
        })
        assert resp.status_code == 200


class TestSessionStatus:
    def test_status_of_created_session(self):
        start = client.post("/api/verdict/start", json={"question": "Should we expand to Europe?"}).json()
        resp = client.get(f"/api/verdict/{start['session_id']}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

    def test_status_of_nonexistent_session(self):
        resp = client.get("/api/verdict/nonexistent-id/status")
        assert resp.status_code == 404


class TestFormats:
    def test_formats_returns_list(self):
        resp = client.get("/api/verdict/formats")
        assert resp.status_code == 200
        formats = resp.json()["formats"]
        ids = [f["id"] for f in formats]
        assert "executive" in ids
        assert "technical" in ids
        assert "legal" in ids
        assert "investor" in ids


class TestHistory:
    def test_history_returns_sessions(self):
        client.post("/api/verdict/start", json={"question": "Should we launch a new product line?"})
        resp = client.get("/api/verdict/sessions/history")
        assert resp.status_code == 200
        assert len(resp.json()["sessions"]) > 0


class TestExportErrors:
    def test_export_incomplete_session_returns_202(self):
        start = client.post("/api/verdict/start", json={"question": "Should we adopt microservices?"}).json()
        sid = start["session_id"]
        resp = client.get(f"/api/verdict/{sid}/export/markdown")
        assert resp.status_code == 202

    def test_export_nonexistent_returns_404(self):
        resp = client.get("/api/verdict/fake-id/export/pdf")
        assert resp.status_code == 404


class TestShareEndpoint:
    def test_share_incomplete_returns_202(self):
        start = client.post("/api/verdict/start", json={"question": "Should we open-source our core library?"}).json()
        resp = client.get(f"/api/verdict/{start['session_id']}/share")
        assert resp.status_code == 202

    def test_shared_nonexistent_returns_404(self):
        resp = client.get("/api/verdict/shared/nonexistent")
        assert resp.status_code == 404
