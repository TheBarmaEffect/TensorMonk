"""Shared test fixtures and configuration for the Verdict test suite.

Configures pytest paths and provides common test fixtures used across
multiple test files.
"""

import sys
import os
import pytest

# Ensure backend/ is on the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_claims():
    """Provide standard test claims for argument quality and graph tests."""
    return [
        {"id": "p1", "statement": "Market growing at 25% CAGR", "evidence": "Gartner 2024 report", "confidence": 0.85},
        {"id": "p2", "statement": "Customer retention exceeds 90%", "evidence": "Internal metrics", "confidence": 0.80},
    ]
