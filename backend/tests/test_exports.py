"""Tests for export service — domain PDF themes, markdown, JSON, DOCX generation."""

import pytest
from services.export_service import (
    generate_markdown_report,
    generate_json_report,
    generate_pdf_report,
    generate_docx_report,
    DOMAIN_PDF_THEMES,
)


SAMPLE_SESSION = {
    "decision": {"id": "test-123", "question": "Should we pivot to B2B?"},
    "research_package": {
        "summary": "Market analysis shows B2B potential.",
        "key_data_points": ["TAM $50B", "Growing 20% YoY"],
        "risk_landscape": ["Regulatory risk", "Market saturation"],
    },
    "prosecutor_argument": {
        "agent": "prosecutor",
        "opening": "The evidence clearly supports this pivot.",
        "claims": [
            {"id": "c1", "statement": "Revenue growth", "evidence": "40% QoQ", "confidence": 0.9},
            {"id": "c2", "statement": "Market fit", "evidence": "NPS 72", "confidence": 0.8},
        ],
        "closing": "We should proceed.",
        "confidence": 0.85,
    },
    "defense_argument": {
        "agent": "defense",
        "opening": "There are significant risks to consider.",
        "claims": [
            {"id": "c3", "statement": "Churn risk", "evidence": "B2B churn 15%", "confidence": 0.7},
        ],
        "closing": "We should not proceed without mitigation.",
        "confidence": 0.7,
    },
    "witness_reports": [
        {"claim_id": "c1", "witness_type": "fact", "verdict_on_claim": "sustained", "resolution": "Verified", "confidence": 0.9},
        {"claim_id": "c3", "witness_type": "data", "verdict_on_claim": "overruled", "resolution": "Data contradicts", "confidence": 0.3},
    ],
    "verdict": {
        "decision_id": "test-123",
        "ruling": "proceed",
        "confidence": 0.82,
        "reasoning": "Strong evidence supports moving forward.",
        "key_factors": ["Market growth", "Team readiness"],
        "dissenting_points": ["Regulatory risk"],
    },
    "synthesis": {
        "decision_id": "test-123",
        "improved_idea": "Pivot to B2B with phased rollout.",
        "strength_score": 0.88,
        "addressed_objections": ["Regulatory compliance via WorkOS"],
        "recommended_actions": ["Week 1: SSO", "Week 2: Beta"],
    },
    "output_format": "executive",
    "domain": "business",
}


class TestDomainPDFThemes:
    """Verify all 9 domain themes are defined correctly."""

    def test_all_nine_domains_present(self):
        expected = ["business", "financial", "legal", "medical", "technology",
                    "hiring", "strategic", "product", "marketing"]
        for domain in expected:
            assert domain in DOMAIN_PDF_THEMES, f"Missing domain: {domain}"

    def test_each_theme_has_accent_and_subtitle(self):
        for domain, theme in DOMAIN_PDF_THEMES.items():
            assert "accent" in theme, f"{domain} missing accent"
            assert "subtitle" in theme, f"{domain} missing subtitle"
            assert isinstance(theme["accent"], tuple), f"{domain} accent should be tuple"
            assert len(theme["accent"]) == 3, f"{domain} accent should be RGB tuple"
            assert isinstance(theme["subtitle"], str), f"{domain} subtitle should be string"

    def test_accent_values_in_range(self):
        for domain, theme in DOMAIN_PDF_THEMES.items():
            for channel in theme["accent"]:
                assert 0 <= channel <= 255, f"{domain} accent channel {channel} out of range"


class TestMarkdownExport:
    def test_generates_markdown(self):
        md = generate_markdown_report(SAMPLE_SESSION)
        assert "VERDICT" in md
        assert "Should we pivot to B2B?" in md
        assert "Research Analysis" in md
        assert "Prosecution Arguments" in md
        assert "Defense Arguments" in md
        assert "Final Verdict" in md
        assert "PROCEED" in md

    def test_includes_claims(self):
        md = generate_markdown_report(SAMPLE_SESSION)
        assert "Revenue growth" in md
        assert "Churn risk" in md

    def test_includes_witnesses(self):
        md = generate_markdown_report(SAMPLE_SESSION)
        assert "SUSTAINED" in md
        assert "OVERRULED" in md

    def test_includes_stability_metrics_when_present(self):
        session = {**SAMPLE_SESSION, "analysis": {
            "verdict_stability": {
                "combined_robustness": 0.85,
                "verdict_is_robust": True,
                "evidence_margin": "moderate",
                "flip_rate": 0.04,
            },
            "argument_quality": {
                "prosecutor": {"grade": "B", "overall": 0.72},
                "defense": {"grade": "C", "overall": 0.48},
                "quality_gap": 0.24,
                "weaker_side": "defense",
            },
        }}
        md = generate_markdown_report(session)
        assert "Analysis & Quality Metrics" in md
        assert "Robustness Score" in md
        assert "Prosecution Grade" in md
        assert "Quality Gap" in md

    def test_omits_stability_when_absent(self):
        md = generate_markdown_report(SAMPLE_SESSION)
        assert "Analysis & Quality Metrics" not in md

    def test_includes_word_count_and_reading_time(self):
        md = generate_markdown_report(SAMPLE_SESSION)
        assert "words" in md
        assert "min read" in md


class TestJSONExport:
    def test_generates_valid_json(self):
        import json
        result = generate_json_report(SAMPLE_SESSION)
        parsed = json.loads(result)
        assert parsed["domain"] == "business"
        assert parsed["verdict"]["ruling"] == "proceed"


class TestPDFExport:
    def test_generates_pdf_bytes(self):
        pdf = generate_pdf_report(SAMPLE_SESSION)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100
        assert pdf[:5] == b'%PDF-'

    def test_pdf_with_each_domain(self):
        """Each domain should produce a valid PDF without errors."""
        for domain in DOMAIN_PDF_THEMES:
            session = {**SAMPLE_SESSION, "domain": domain}
            pdf = generate_pdf_report(session)
            assert pdf[:5] == b'%PDF-', f"Failed for domain: {domain}"

    def test_pdf_with_unknown_domain_falls_back(self):
        session = {**SAMPLE_SESSION, "domain": "unknown_domain"}
        pdf = generate_pdf_report(session)
        assert pdf[:5] == b'%PDF-'


class TestDOCXExport:
    def test_generates_docx_bytes(self):
        docx = generate_docx_report(SAMPLE_SESSION)
        assert isinstance(docx, bytes)
        assert len(docx) > 100
        # DOCX files start with PK (ZIP format)
        assert docx[:2] == b'PK'
