"""Tests for input validators — question quality, format-domain fit, and package completeness."""

import pytest
from utils.validators import (
    validate_question_quality,
    validate_research_package,
    check_format_domain_fit,
    is_valid_domain,
    VALID_DOMAINS,
)


class TestQuestionQuality:
    """Test question quality validation."""

    def test_accepts_good_question(self):
        ok, err = validate_question_quality("Should we pivot from B2C to B2B SaaS?")
        assert ok is True
        assert err is None

    def test_rejects_yes(self):
        ok, err = validate_question_quality("yes")
        assert ok is False

    def test_rejects_test(self):
        ok, err = validate_question_quality("test")
        assert ok is False

    def test_rejects_hello(self):
        ok, err = validate_question_quality("hello?")
        assert ok is False

    def test_accepts_long_non_decision(self):
        # Long enough to pass even without decision words
        ok, _ = validate_question_quality(
            "The current market conditions in the renewable energy sector show interesting trends for solar"
        )
        assert ok is True

    def test_accepts_should_question(self):
        ok, _ = validate_question_quality("Should I accept the acquisition offer?")
        assert ok is True

    def test_accepts_invest_question(self):
        ok, _ = validate_question_quality("Is it worth investing in quantum computing research?")
        assert ok is True


class TestResearchPackageValidation:
    """Test research package completeness."""

    def test_complete_package_is_valid(self):
        package = {
            "market_context": "Growing market",
            "key_data_points": ["50% growth"],
            "precedents": ["Company X did this"],
            "stakeholders": ["Team", "Customers"],
            "risk_landscape": ["Competition"],
            "summary": "Overall positive outlook",
        }
        ok, missing = validate_research_package(package)
        assert ok is True
        assert missing == []

    def test_missing_field_detected(self):
        package = {"market_context": "Growing"}
        ok, missing = validate_research_package(package)
        assert ok is False
        assert len(missing) > 0

    def test_empty_string_field_detected(self):
        package = {
            "market_context": "",
            "key_data_points": ["data"],
            "precedents": ["p"],
            "stakeholders": ["s"],
            "risk_landscape": ["r"],
            "summary": "summary",
        }
        ok, missing = validate_research_package(package)
        assert ok is False
        assert "market_context (empty)" in missing

    def test_empty_list_field_detected(self):
        package = {
            "market_context": "context",
            "key_data_points": [],
            "precedents": ["p"],
            "stakeholders": ["s"],
            "risk_landscape": ["r"],
            "summary": "summary",
        }
        ok, missing = validate_research_package(package)
        assert ok is False


class TestFormatDomainFit:
    """Test format-domain compatibility checking."""

    def test_executive_fits_business(self):
        ok, _ = check_format_domain_fit("executive", "business")
        assert ok is True

    def test_technical_fits_technology(self):
        ok, _ = check_format_domain_fit("technical", "technology")
        assert ok is True

    def test_legal_fits_legal(self):
        ok, _ = check_format_domain_fit("legal", "legal")
        assert ok is True

    def test_investor_fits_financial(self):
        ok, _ = check_format_domain_fit("investor", "financial")
        assert ok is True

    def test_mismatch_provides_suggestion(self):
        ok, suggestion = check_format_domain_fit("legal", "technology")
        # Either fits or provides a suggestion
        if not ok:
            assert suggestion is not None
            assert "technical" in suggestion.lower()

    def test_always_returns_tuple(self):
        ok, suggestion = check_format_domain_fit("executive", "business")
        assert isinstance(ok, bool)


class TestDomainValidation:
    """Test domain string validation."""

    def test_all_valid_domains(self):
        for domain in VALID_DOMAINS:
            assert is_valid_domain(domain) is True

    def test_invalid_domain(self):
        assert is_valid_domain("nonexistent") is False

    def test_case_insensitive(self):
        assert is_valid_domain("BUSINESS") is True
        assert is_valid_domain("Technology") is True

    def test_strips_whitespace(self):
        assert is_valid_domain(" business ") is True

    def test_valid_domain_count(self):
        assert len(VALID_DOMAINS) == 10
