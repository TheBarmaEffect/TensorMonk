"""Tests for the FastAPI routes — verifying API contract and response shapes."""

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
            "question": "Should we pivot?",
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
            "question": "Should we hire a CTO?",
        })
        data = resp.json()
        assert data["domain"] == "hiring"

    def test_start_detects_financial_domain(self):
        resp = client.post("/api/verdict/start", json={
            "question": "Should we raise a Series A?",
        })
        data = resp.json()
        assert data["domain"] == "financial"


class TestSessionStatus:
    def test_status_of_created_session(self):
        start = client.post("/api/verdict/start", json={"question": "test"}).json()
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
        client.post("/api/verdict/start", json={"question": "test history"})
        resp = client.get("/api/verdict/sessions/history")
        assert resp.status_code == 200
        assert len(resp.json()["sessions"]) > 0


class TestExportErrors:
    def test_export_incomplete_session_returns_202(self):
        start = client.post("/api/verdict/start", json={"question": "test"}).json()
        sid = start["session_id"]
        resp = client.get(f"/api/verdict/{sid}/export/markdown")
        assert resp.status_code == 202

    def test_export_nonexistent_returns_404(self):
        resp = client.get("/api/verdict/fake-id/export/pdf")
        assert resp.status_code == 404


class TestShareEndpoint:
    def test_share_incomplete_returns_202(self):
        start = client.post("/api/verdict/start", json={"question": "test"}).json()
        resp = client.get(f"/api/verdict/{start['session_id']}/share")
        assert resp.status_code == 202

    def test_shared_nonexistent_returns_404(self):
        resp = client.get("/api/verdict/shared/nonexistent")
        assert resp.status_code == 404
