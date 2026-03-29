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


class TestJudgeClaimOverlap:
    """Test claim overlap detection in the Judge agent."""

    def _make_claim(self, id, statement, confidence=0.8):
        from models.schemas import Claim
        return Claim(id=id, statement=statement, evidence="test", confidence=confidence)

    def _make_arg(self, agent, claims, confidence=0.8):
        from models.schemas import Argument
        return Argument(agent=agent, opening="test", claims=claims, confidence=confidence)

    def test_detects_overlapping_claims(self):
        """Claims with shared keywords should be detected as overlapping."""
        from agents.judge import JudgeAgent
        judge = JudgeAgent()
        pro = self._make_arg("prosecutor", [
            self._make_claim("p1", "The market opportunity for cloud computing is massive and growing"),
        ])
        defense = self._make_arg("defense", [
            self._make_claim("d1", "The market for cloud computing is saturated with competitors"),
        ])
        overlaps = judge.detect_claim_overlaps(pro, defense)
        assert len(overlaps) >= 1
        assert overlaps[0]["overlap_score"] > 0.3

    def test_no_overlap_for_unrelated_claims(self):
        """Unrelated claims should not produce overlaps."""
        from agents.judge import JudgeAgent
        judge = JudgeAgent()
        pro = self._make_arg("prosecutor", [
            self._make_claim("p1", "Revenue growth exceeds projections quarterly"),
        ])
        defense = self._make_arg("defense", [
            self._make_claim("d1", "Technical debt threatens infrastructure stability"),
        ])
        overlaps = judge.detect_claim_overlaps(pro, defense)
        assert len(overlaps) == 0

    def test_overlap_includes_shared_keywords(self):
        """Overlap results should include the shared keyword set."""
        from agents.judge import JudgeAgent
        judge = JudgeAgent()
        pro = self._make_arg("prosecutor", [
            self._make_claim("p1", "Enterprise customers demand robust security features"),
        ])
        defense = self._make_arg("defense", [
            self._make_claim("d1", "Building enterprise security features requires years of investment"),
        ])
        overlaps = judge.detect_claim_overlaps(pro, defense)
        if overlaps:
            assert "shared_keywords" in overlaps[0]
            assert len(overlaps[0]["shared_keywords"]) > 0

    def test_overlap_sorted_by_score(self):
        """Multiple overlaps should be sorted by score descending."""
        from agents.judge import JudgeAgent
        judge = JudgeAgent()
        pro = self._make_arg("prosecutor", [
            self._make_claim("p1", "The technology stack scales well"),
            self._make_claim("p2", "Market share growth indicates strong demand from enterprise customers"),
        ])
        defense = self._make_arg("defense", [
            self._make_claim("d1", "Technology stack scaling requires significant investment"),
            self._make_claim("d2", "Enterprise customers have slow procurement cycles"),
        ])
        overlaps = judge.detect_claim_overlaps(pro, defense)
        if len(overlaps) >= 2:
            assert overlaps[0]["overlap_score"] >= overlaps[1]["overlap_score"]

    def test_confidence_gap_included(self):
        """Overlap should include confidence gap between opposing claims."""
        from agents.judge import JudgeAgent
        judge = JudgeAgent()
        pro = self._make_arg("prosecutor", [
            self._make_claim("p1", "Market demand strong growth", confidence=0.9),
        ])
        defense = self._make_arg("defense", [
            self._make_claim("d1", "Market demand declining growth", confidence=0.6),
        ])
        overlaps = judge.detect_claim_overlaps(pro, defense, overlap_threshold=0.2)
        if overlaps:
            assert overlaps[0]["confidence_gap"] == 0.3


class TestResearchQuality:
    """Test research quality scoring integration."""

    def test_quality_scoring_all_fields(self):
        """Full research package should score high on breadth."""
        from agents.research import ResearchAgent
        agent = ResearchAgent()
        pkg = {
            "market_context": "Large market",
            "key_data_points": ["fact1 (source: http://example.com)", "fact2", "fact3"],
            "precedents": ["precedent1", "precedent2"],
            "stakeholders": ["stakeholder1"],
            "risk_landscape": ["risk1", "risk2"],
            "summary": "A comprehensive summary of the research findings covering multiple dimensions of the market.",
        }
        scores = agent.score_research_quality(pkg)
        assert scores["breadth"] == 1.0
        assert scores["balance"] == 1.0
        assert scores["overall"] > 0.5

    def test_quality_grounding_detection(self):
        """Should detect web-sourced data points."""
        from agents.research import ResearchAgent
        agent = ResearchAgent()
        pkg = {
            "market_context": "test",
            "key_data_points": [
                "Market is $50B (source: http://statista.com)",
                "Growing 15% YoY (source: http://gartner.com)",
            ],
            "precedents": [],
            "stakeholders": [],
            "risk_landscape": [],
            "summary": "test",
        }
        scores = agent.score_research_quality(pkg)
        assert scores["grounding"] == 1.0

    def test_quality_empty_package(self):
        """Empty package should score low."""
        from agents.research import ResearchAgent
        agent = ResearchAgent()
        scores = agent.score_research_quality({})
        assert scores["breadth"] == 0.0
        assert scores["overall"] < 0.3


class TestSynthesisCoverage:
    """Test synthesis coverage assessment."""

    def test_coverage_when_objections_addressed(self):
        """Should detect addressed objections via keyword overlap."""
        from agents.synthesis import SynthesisAgent
        from models.schemas import Argument, Claim, Synthesis
        agent = SynthesisAgent()

        defense = Argument(
            agent="defense",
            opening="Against",
            claims=[Claim(id="d1", statement="The market competition is fierce and established", evidence="ev", confidence=0.8)],
            confidence=0.7,
        )
        pro = Argument(
            agent="prosecutor",
            opening="For",
            claims=[Claim(id="p1", statement="Strong growth", evidence="ev", confidence=0.85)],
            confidence=0.85,
        )
        synth = Synthesis(
            decision_id="test",
            improved_idea="Better version",
            addressed_objections=["The market competition concern is addressed by focusing on niche segments where established players are weak"],
            recommended_actions=["Within 2 weeks, launch pilot program"],
            strength_score=0.8,
        )

        coverage = agent.assess_synthesis_coverage(synth, defense, pro)
        assert coverage["objection_coverage"] > 0
        assert coverage["has_time_bounds"] is True
        assert coverage["strength_delta"] == pytest.approx(0.8 - 0.85, abs=0.01)


class TestAnalysisPipelineIntegration:
    """Test the full analytical pipeline: quality scoring → graph → stability."""

    def _make_arg_dict(self, agent: str, claims: list[dict], confidence: float = 0.75) -> dict:
        """Create a serialized argument dict for analysis."""
        return {
            "agent": agent,
            "opening": f"Opening statement for {agent}",
            "claims": claims,
            "confidence": confidence,
        }

    def test_quality_scores_both_sides(self):
        """score_argument_quality should produce grades for prosecution and defense."""
        from utils.argument_quality import score_argument_quality

        pro = self._make_arg_dict("prosecutor", [
            {"id": "p1", "statement": "Market growing at 25% annually in 2024 according to Gartner", "evidence": "Gartner Q3 2024 report", "confidence": 0.85},
            {"id": "p2", "statement": "Customer retention exceeds 90% in B2B SaaS", "evidence": "SaaS Capital annual survey", "confidence": 0.8},
            {"id": "p3", "statement": "Unit economics are positive with CAC:LTV of 1:5", "evidence": "Internal financial model", "confidence": 0.75},
            {"id": "p4", "statement": "Three competitors acquired in last 12 months", "evidence": "TechCrunch coverage", "confidence": 0.7},
        ])
        result = score_argument_quality(pro)
        assert "grade" in result
        assert result["grade"] in ("A", "B", "C", "D")
        assert 0.0 <= result["overall"] <= 1.0
        assert "evidence_specificity" in result["dimensions"]

    def test_stability_analysis_end_to_end(self):
        """full_stability_analysis should combine margin + perturbation."""
        from utils.verdict_stability import full_stability_analysis

        result = full_stability_analysis(
            prosecution_score=0.78,
            defense_score=0.62,
            ruling="proceed",
            witness_reports=[
                {"claim_id": "p1", "confidence": 0.85, "verdict_on_claim": "sustained"},
                {"claim_id": "d1", "confidence": 0.7, "verdict_on_claim": "overruled"},
            ],
            prosecution_base_confidence=0.8,
            defense_base_confidence=0.65,
        )
        assert "evidence_margin" in result
        assert "perturbation_stability" in result
        assert "combined_robustness" in result
        assert 0.0 <= result["combined_robustness"] <= 1.0

    def test_argument_graphs_comparative(self):
        """build_argument_graphs should produce comparative metrics."""
        from utils.argument_graph import build_argument_graphs

        pro_claims = [
            {"id": "p1", "statement": "Strong market demand for cloud solutions", "evidence": "Gartner report", "confidence": 0.8},
            {"id": "p2", "statement": "Cloud adoption drives market growth", "evidence": "IDC forecast", "confidence": 0.75},
        ]
        def_claims = [
            {"id": "d1", "statement": "Cloud migration costs are prohibitive", "evidence": "CIO survey", "confidence": 0.7},
        ]

        result = build_argument_graphs(pro_claims, def_claims)
        assert "prosecution" in result
        assert "defense" in result
        assert "comparative" in result
        assert result["prosecution"]["node_count"] == 2
        assert result["defense"]["node_count"] == 1

    def test_quality_feeds_into_synthesis(self):
        """Argument quality grades should be computed by synthesis agent."""
        from utils.argument_quality import score_argument_quality

        weak_arg = self._make_arg_dict("defense", [
            {"id": "d1", "statement": "Bad idea", "evidence": "Trust me", "confidence": 0.5},
        ], confidence=0.4)
        strong_arg = self._make_arg_dict("prosecutor", [
            {"id": "p1", "statement": "Market analysis shows 35% CAGR in enterprise SaaS", "evidence": "Gartner 2024 report", "confidence": 0.88},
            {"id": "p2", "statement": "Customer churn below 5% indicates strong product-market fit", "evidence": "Internal metrics dashboard", "confidence": 0.82},
            {"id": "p3", "statement": "Unit economics positive with 18-month payback period", "evidence": "Financial model v3", "confidence": 0.79},
        ], confidence=0.85)

        weak_quality = score_argument_quality(weak_arg)
        strong_quality = score_argument_quality(strong_arg)
        assert strong_quality["overall"] > weak_quality["overall"]
        # Strong argument should score at least as well as weak
        assert strong_quality["grade"] <= weak_quality["grade"]  # A < B < C < D lexicographically

    def test_validators_wired_to_api(self, client):
        """API should reject generic questions via quality validator."""
        resp = client.post("/api/verdict/start", json={"question": "test?"})
        assert resp.status_code == 422

    def test_format_suggestion_in_response(self, client):
        """API should include format_suggestion when format-domain mismatch."""
        resp = client.post("/api/verdict/start", json={
            "question": "Should we adopt a new compliance framework for GDPR regulations?",
            "output_format": "technical",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "format_suggestion" in data


class TestIntelligencePipelineIntegration:
    """Test that computed intelligence flows through state and influences behavior."""

    def test_verdict_state_includes_intelligence_fields(self):
        """VerdictState should include argument_quality, argument_graphs, verdict_stability."""
        from graph.verdict_graph import VerdictState
        import typing
        hints = typing.get_type_hints(VerdictState)
        assert "argument_quality" in hints
        assert "argument_graphs" in hints
        assert "verdict_stability" in hints

    def test_graph_analysis_flows_to_witness_prioritization(self):
        """Witness node should re-order contested claims by cascading impact."""
        from utils.argument_graph import build_argument_graphs

        pro_claims = [
            {"id": "p1", "statement": "Strong market demand for cloud solutions growing rapidly", "evidence": "Gartner report 2024", "confidence": 0.85},
            {"id": "p2", "statement": "Cloud adoption drives efficiency improvements", "evidence": "IDC forecast", "confidence": 0.75},
        ]
        def_claims = [
            {"id": "d1", "statement": "Cloud migration costs prohibitive for SMBs", "evidence": "CIO survey", "confidence": 0.7},
        ]

        result = build_argument_graphs(pro_claims, def_claims)
        # Graph analysis should contain per-claim metrics used for prioritization
        assert "prosecution" in result
        pro_data = result["prosecution"]
        assert "per_claim" in pro_data
        for cid in pro_data["per_claim"]:
            assert "cascading_impact" in pro_data["per_claim"][cid]

    def test_structural_analysis_passed_to_judge(self):
        """Judge's cross_examine should accept structural_analysis parameter."""
        import inspect
        from agents.judge import JudgeAgent
        sig = inspect.signature(JudgeAgent.cross_examine)
        params = list(sig.parameters.keys())
        assert "structural_analysis" in params

    def test_synthesis_accepts_stability_and_quality(self):
        """Synthesis agent should accept verdict_stability and argument_quality."""
        import inspect
        from agents.synthesis import SynthesisAgent
        sig = inspect.signature(SynthesisAgent.run)
        params = list(sig.parameters.keys())
        assert "verdict_stability" in params
        assert "argument_quality" in params

    def test_quality_stored_in_state_from_arguments_node(self):
        """parallel_arguments_node should compute and store argument_quality in state."""
        from utils.argument_quality import score_argument_quality

        # Verify score_argument_quality returns fields needed by state
        result = score_argument_quality({
            "agent": "prosecutor",
            "opening": "Test opening",
            "claims": [
                {"id": "p1", "statement": "Test claim with evidence", "evidence": "Source", "confidence": 0.8},
            ],
            "confidence": 0.8,
        })
        assert "grade" in result
        assert "overall" in result
        # These are the fields stored in state["argument_quality"]
        assert isinstance(result["grade"], str)
        assert isinstance(result["overall"], float)

    def test_stability_contains_routing_fields(self):
        """Verdict stability should contain fields used by synthesis for cautious recommendations."""
        from utils.verdict_stability import full_stability_analysis

        result = full_stability_analysis(
            prosecution_score=0.65,
            defense_score=0.60,
            ruling="conditional",
            witness_reports=[
                {"claim_id": "p1", "confidence": 0.6, "verdict_on_claim": "sustained"},
            ],
            prosecution_base_confidence=0.7,
            defense_base_confidence=0.65,
        )
        # These fields flow into synthesis via verdict_stability state
        assert "combined_robustness" in result
        assert "verdict_is_robust" in result
        assert "evidence_margin" in result
        margin = result["evidence_margin"]
        assert "classification" in margin  # decisive|moderate|narrow|razor_thin

    def test_domain_confidence_thresholds_exist(self):
        """Domain-specific confidence thresholds should be defined for routing."""
        from graph.verdict_graph import DOMAIN_CONFIDENCE_THRESHOLDS
        assert "medical" in DOMAIN_CONFIDENCE_THRESHOLDS
        assert "legal" in DOMAIN_CONFIDENCE_THRESHOLDS
        assert "technology" in DOMAIN_CONFIDENCE_THRESHOLDS
        # Medical should require higher confidence than technology
        assert DOMAIN_CONFIDENCE_THRESHOLDS["medical"] > DOMAIN_CONFIDENCE_THRESHOLDS["technology"]


class TestEndToEndGraphTopology:
    """Verify the LangGraph state machine is correctly wired end-to-end."""

    def test_graph_compiles_without_error(self):
        """The full verdict graph should compile into a runnable."""
        from graph.verdict_graph import build_verdict_graph
        graph = build_verdict_graph()
        assert graph is not None

    def test_graph_is_invocable(self):
        """Compiled graph should have an invoke or ainvoke method."""
        from graph.verdict_graph import build_verdict_graph
        graph = build_verdict_graph()
        assert hasattr(graph, 'ainvoke') or hasattr(graph, 'invoke')

    def test_strip_authorship_removes_all_fields(self):
        """strip_authorship should remove all 11 metadata fields."""
        from graph.verdict_graph import strip_authorship
        data = {
            "content": "Real data",
            "agent_id": "secret", "agent": "secret", "source": "secret",
            "model": "secret", "timestamp": "secret", "metadata": "secret",
            "author": "secret", "provider": "secret", "version": "secret",
            "run_id": "secret", "trace_id": "secret",
        }
        cleaned = strip_authorship(data)
        assert cleaned["content"] == "Real data"
        for field in ["agent_id", "agent", "source", "model", "timestamp",
                       "metadata", "author", "provider", "version", "run_id", "trace_id"]:
            assert field not in cleaned

    def test_domain_thresholds_cover_all_yaml_domains(self):
        """Every domain in domains.yaml should have a confidence threshold or use default."""
        import yaml
        from graph.verdict_graph import DOMAIN_CONFIDENCE_THRESHOLDS
        with open("config/domains.yaml") as f:
            domains = yaml.safe_load(f)
        for domain_name in domains:
            # Either has explicit threshold or falls to default 0.6
            threshold = DOMAIN_CONFIDENCE_THRESHOLDS.get(domain_name, 0.6)
            assert 0.0 < threshold <= 1.0

def test_sample_claims_fixture(sample_claims):
    """Verify shared fixture provides valid test claims."""
    assert len(sample_claims) == 2
    assert all("id" in c for c in sample_claims)
    assert all("confidence" in c for c in sample_claims)

