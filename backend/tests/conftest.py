"""Shared pytest fixtures for the Verdict test suite.

Provides reusable test data (sample sessions, claims, arguments) and
configured test clients to reduce duplication across test files.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI test client for API endpoint testing."""
    return TestClient(app)


@pytest.fixture
def sample_decision():
    """Sample decision input for testing."""
    return {
        "id": "test-decision-001",
        "question": "Should we pivot our SaaS from B2C to B2B?",
        "context": "Early-stage startup, $500K ARR, 200 customers",
    }


@pytest.fixture
def sample_claims():
    """Sample claims for prosecutor/defense argument testing."""
    return [
        {"id": "c1", "statement": "Revenue growth is strong", "evidence": "40% QoQ growth", "confidence": 0.9},
        {"id": "c2", "statement": "Market fit validated", "evidence": "NPS score of 72", "confidence": 0.8},
        {"id": "c3", "statement": "Churn risk is significant", "evidence": "B2B churn at 15%", "confidence": 0.7},
    ]


@pytest.fixture
def sample_session(sample_decision, sample_claims):
    """Complete sample session data for export and result testing."""
    return {
        "decision": sample_decision,
        "output_format": "executive",
        "domain": "business",
        "status": "complete",
        "research_package": {
            "summary": "Market analysis indicates strong B2B potential.",
            "key_data_points": ["TAM $50B", "Growing 20% YoY", "3 key competitors"],
            "risk_landscape": ["Regulatory changes", "Market saturation risk"],
        },
        "prosecutor_argument": {
            "agent": "prosecutor",
            "opening": "The evidence clearly supports this strategic pivot.",
            "claims": sample_claims[:2],
            "closing": "We recommend proceeding with the pivot.",
            "confidence": 0.85,
        },
        "defense_argument": {
            "agent": "defense",
            "opening": "Significant risks warrant caution.",
            "claims": [sample_claims[2]],
            "closing": "We recommend against proceeding without mitigation.",
            "confidence": 0.7,
        },
        "witness_reports": [
            {
                "claim_id": "c1",
                "witness_type": "fact",
                "verdict_on_claim": "sustained",
                "resolution": "Revenue data verified from financial statements.",
                "confidence": 0.92,
            },
            {
                "claim_id": "c3",
                "witness_type": "data",
                "verdict_on_claim": "overruled",
                "resolution": "Industry benchmarks show B2B churn is actually 8-10%.",
                "confidence": 0.78,
            },
        ],
        "verdict": {
            "decision_id": "test-decision-001",
            "ruling": "proceed",
            "confidence": 0.82,
            "reasoning": "Evidence strongly supports the pivot with manageable risks.",
            "key_factors": ["Strong revenue trajectory", "Market fit validated", "Churn lower than claimed"],
            "dissenting_points": ["Regulatory landscape needs monitoring"],
        },
        "synthesis": {
            "decision_id": "test-decision-001",
            "improved_idea": "Pivot to B2B with phased enterprise rollout over 3 months.",
            "strength_score": 0.88,
            "addressed_objections": ["Churn mitigated via annual contracts", "Regulatory compliance via WorkOS SSO"],
            "recommended_actions": ["Week 1-2: Enterprise SSO", "Week 3-4: Beta with 5 clients", "Month 2: Scale to 20"],
        },
    }
