"""Tests for security middleware — XSS detection, sanitization, headers."""

import pytest
from middleware.security import (
    contains_xss_pattern,
    sanitize_input,
    SecurityMiddleware,
    _SECURITY_HEADERS,
)


class TestXSSDetection:
    """Test XSS pattern detection."""

    def test_detects_script_tag(self):
        assert contains_xss_pattern('<script>alert("xss")</script>') is True

    def test_detects_script_tag_case_insensitive(self):
        assert contains_xss_pattern('<SCRIPT>alert(1)</SCRIPT>') is True

    def test_detects_javascript_protocol(self):
        assert contains_xss_pattern('javascript:alert(1)') is True

    def test_detects_event_handler(self):
        assert contains_xss_pattern('onerror=alert(1)') is True
        assert contains_xss_pattern('onclick = steal()') is True

    def test_detects_iframe(self):
        assert contains_xss_pattern('<iframe src="evil.com">') is True

    def test_detects_eval(self):
        assert contains_xss_pattern('eval(document.cookie)') is True

    def test_detects_document_cookie(self):
        assert contains_xss_pattern('document.cookie') is True

    def test_allows_clean_input(self):
        assert contains_xss_pattern('Should I pivot my SaaS to B2B?') is False

    def test_allows_normal_html_entities(self):
        assert contains_xss_pattern('revenue &gt; $1M') is False

    def test_allows_technical_questions(self):
        assert contains_xss_pattern('Should we migrate to React 18?') is False


class TestSanitizeInput:
    """Test HTML entity escaping."""

    def test_escapes_angle_brackets(self):
        assert sanitize_input('<script>') == '&lt;script&gt;'

    def test_escapes_ampersand(self):
        assert sanitize_input('A & B') == 'A &amp; B'

    def test_escapes_quotes(self):
        assert sanitize_input('"hello"') == '&quot;hello&quot;'

    def test_escapes_single_quotes(self):
        assert sanitize_input("it's") == "it&#x27;s"

    def test_handles_empty_string(self):
        assert sanitize_input('') == ''

    def test_handles_none(self):
        assert sanitize_input(None) is None

    def test_preserves_clean_text(self):
        text = 'Should we raise a Series A?'
        assert sanitize_input(text) == text

    def test_compound_escaping(self):
        result = sanitize_input('<img onerror="alert(1)">')
        assert '<' not in result
        assert '>' not in result
        assert '"' not in result


class TestSecurityHeaders:
    """Verify security header configuration."""

    def test_nosniff_header_defined(self):
        assert _SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"

    def test_frame_deny_header_defined(self):
        assert _SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_xss_protection_header_defined(self):
        assert "1; mode=block" in _SECURITY_HEADERS["X-XSS-Protection"]

    def test_referrer_policy_defined(self):
        assert "strict-origin" in _SECURITY_HEADERS["Referrer-Policy"]
