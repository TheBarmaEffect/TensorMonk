"""Tests for centralized prompt templates — validates constitutional directives."""

import pytest
from agents.prompts import (
    RESEARCH_SYSTEM,
    PROSECUTOR_SYSTEM,
    DEFENSE_SYSTEM,
    JUDGE_CROSS_EXAM_SYSTEM,
    JUDGE_VERDICT_SYSTEM,
    WITNESS_SYSTEM,
    SYNTHESIS_SYSTEM,
    FORMAT_INSTRUCTIONS,
    PROMPT_VERSION,
    get_format_instruction,
)


class TestConstitutionalDirectives:
    """Verify that constitutional directives are present in all agent prompts."""

    def test_research_is_neutral(self):
        assert "neutral" in RESEARCH_SYSTEM.lower()
        assert "CONSTITUTIONAL DIRECTIVE" in RESEARCH_SYSTEM

    def test_prosecutor_argues_for(self):
        assert "MUST argue FOR" in PROSECUTOR_SYSTEM
        assert "CONSTITUTIONAL DIRECTIVE" in PROSECUTOR_SYSTEM

    def test_defense_argues_against(self):
        assert "MUST argue AGAINST" in DEFENSE_SYSTEM
        assert "CONSTITUTIONAL DIRECTIVE" in DEFENSE_SYSTEM

    def test_adversarial_isolation_in_prosecutor(self):
        assert "ADVERSARIAL ISOLATION" in PROSECUTOR_SYSTEM
        assert "NO access to the defense" in PROSECUTOR_SYSTEM

    def test_adversarial_isolation_in_defense(self):
        assert "ADVERSARIAL ISOLATION" in DEFENSE_SYSTEM
        assert "NO access to the prosecution" in DEFENSE_SYSTEM

    def test_judge_cross_exam_identifies_contested(self):
        assert "CONTESTED CLAIMS" in JUDGE_CROSS_EXAM_SYSTEM

    def test_judge_verdict_delivers_ruling(self):
        assert "FINAL VERDICT" in JUDGE_VERDICT_SYSTEM
        assert "ruling" in JUDGE_VERDICT_SYSTEM

    def test_witness_has_specialty_slot(self):
        assert "{witness_type}" in WITNESS_SYSTEM

    def test_synthesis_preserves_both_sides(self):
        assert "prosecution" in SYNTHESIS_SYSTEM.lower()
        assert "defense" in SYNTHESIS_SYSTEM.lower()
        assert "BATTLE-TESTED" in SYNTHESIS_SYSTEM


class TestPromptStructure:
    """Verify prompts request JSON output and have expected format."""

    def test_research_requests_json(self):
        assert "JSON" in RESEARCH_SYSTEM

    def test_prosecutor_requests_json(self):
        assert "JSON" in PROSECUTOR_SYSTEM

    def test_defense_requests_json(self):
        assert "JSON" in DEFENSE_SYSTEM

    def test_judge_requests_json_array(self):
        assert "JSON" in JUDGE_CROSS_EXAM_SYSTEM

    def test_witness_requests_json(self):
        assert "JSON" in WITNESS_SYSTEM

    def test_synthesis_requests_json(self):
        assert "JSON" in SYNTHESIS_SYSTEM

    def test_all_prompts_have_domain_overlay_slot(self):
        """Prosecutor, defense, and synthesis accept domain overlays."""
        assert "{domain_overlay}" in PROSECUTOR_SYSTEM
        assert "{domain_overlay}" in DEFENSE_SYSTEM
        assert "{domain_overlay}" in SYNTHESIS_SYSTEM


class TestFormatInstructions:
    """Test format instruction helper."""

    def test_executive_format(self):
        result = get_format_instruction("executive")
        assert "strategic" in result.lower()

    def test_technical_format(self):
        result = get_format_instruction("technical")
        assert "technical" in result.lower()

    def test_legal_format(self):
        result = get_format_instruction("legal")
        assert "legal" in result.lower() or "regulatory" in result.lower()

    def test_investor_format(self):
        result = get_format_instruction("investor")
        assert "market" in result.lower() or "financial" in result.lower()

    def test_unknown_format_returns_empty(self):
        assert get_format_instruction("unknown") == ""

    def test_all_four_formats_defined(self):
        assert set(FORMAT_INSTRUCTIONS.keys()) == {"executive", "technical", "legal", "investor"}


class TestPromptVersion:
    """Verify prompt version tracking for audit trail."""

    def test_version_is_semver(self):
        parts = PROMPT_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_version_matches_app(self):
        assert PROMPT_VERSION == "1.4.0"
