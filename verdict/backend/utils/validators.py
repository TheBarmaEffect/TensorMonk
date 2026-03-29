"""Input validators — domain-specific validation rules for the Verdict pipeline.

Provides validation utilities beyond Pydantic field constraints, including:
- Decision question quality scoring
- Domain-specific content validation
- Output format compatibility checks
- Research package completeness verification

These validators run at the API layer to catch issues before the expensive
LLM pipeline starts, providing immediate user feedback.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum meaningful question patterns — questions that are too generic
# to produce useful adversarial analysis
_TOO_GENERIC_PATTERNS = [
    re.compile(r'^(yes|no|maybe|idk|help|test|hello|hi)\s*[?!.]*$', re.IGNORECASE),
    re.compile(r'^(should i|what if)\s*[?!.]*$', re.IGNORECASE),
    re.compile(r'^[a-z]{1,5}\s*[?!.]*$', re.IGNORECASE),
]

# Supported domains for validation
VALID_DOMAINS = frozenset({
    "business", "technology", "legal", "medical", "financial",
    "product", "hiring", "operations", "marketing", "strategic",
})

# Format-domain compatibility matrix — some formats work better with certain domains
FORMAT_DOMAIN_COMPATIBILITY: dict[str, set[str]] = {
    "executive": {"business", "strategic", "operations", "product", "marketing"},
    "technical": {"technology", "product"},
    "legal": {"legal", "hiring"},
    "investor": {"financial", "business", "strategic"},
}


def validate_question_quality(question: str) -> tuple[bool, Optional[str]]:
    """Validate that a question is meaningful enough for adversarial analysis.

    Checks beyond simple length validation:
    - Not a trivially generic question
    - Contains at least one decision-related word
    - Has enough substance for multiple perspectives

    Args:
        question: The user's decision question.

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    q = question.strip()

    # Check against generic patterns
    for pattern in _TOO_GENERIC_PATTERNS:
        if pattern.match(q):
            return False, (
                "Question is too generic for meaningful analysis. "
                "Please describe a specific decision or idea to evaluate."
            )

    # Check for decision-related content
    decision_indicators = (
        "should", "would", "could", "will", "can",
        "decide", "choose", "invest", "hire", "build",
        "launch", "pivot", "expand", "acquire", "migrate",
        "adopt", "implement", "switch", "accept", "reject",
    )
    q_lower = q.lower()
    has_decision_content = any(word in q_lower for word in decision_indicators)

    if not has_decision_content and len(q) < 50:
        return False, (
            "Your input doesn't appear to describe a decision. "
            "Try framing it as 'Should we...?' or 'Is it worth...?'"
        )

    return True, None


def validate_research_package(package: dict) -> tuple[bool, list[str]]:
    """Validate completeness of a research package before adversarial agents run.

    Checks that all required fields exist and have meaningful content.

    Args:
        package: The research package dict from the ResearchAgent.

    Returns:
        Tuple of (is_complete, missing_fields).
    """
    required_fields = [
        "market_context", "key_data_points", "precedents",
        "stakeholders", "risk_landscape", "summary",
    ]

    missing = []
    for field in required_fields:
        if field not in package:
            missing.append(field)
        elif isinstance(package[field], str) and len(package[field].strip()) == 0:
            missing.append(f"{field} (empty)")
        elif isinstance(package[field], list) and len(package[field]) == 0:
            missing.append(f"{field} (empty list)")

    return len(missing) == 0, missing


def check_format_domain_fit(
    output_format: str, domain: str
) -> tuple[bool, Optional[str]]:
    """Check if the output format is a good fit for the detected domain.

    Returns a compatibility assessment — doesn't block execution, just
    provides a suggestion for better results.

    Args:
        output_format: Requested output format (executive/technical/legal/investor).
        domain: Detected decision domain.

    Returns:
        Tuple of (is_good_fit, suggestion). suggestion is None if good fit.
    """
    compatible = FORMAT_DOMAIN_COMPATIBILITY.get(output_format, set())

    if domain in compatible:
        return True, None

    # Find better-fitting formats
    better_formats = []
    for fmt, domains in FORMAT_DOMAIN_COMPATIBILITY.items():
        if domain in domains and fmt != output_format:
            better_formats.append(fmt)

    if better_formats:
        suggestion = (
            f"The '{output_format}' format works, but '{better_formats[0]}' "
            f"may produce better results for {domain} domain decisions."
        )
        return False, suggestion

    return True, None


def is_valid_domain(domain: str) -> bool:
    """Check if a domain string is a recognized domain.

    Args:
        domain: Domain string to validate.

    Returns:
        True if the domain is in the recognized set.
    """
    return domain.lower().strip() in VALID_DOMAINS
