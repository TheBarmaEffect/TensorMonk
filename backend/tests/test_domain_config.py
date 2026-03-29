"""Tests for domain configuration — verify all domains load correctly."""

import pytest
import yaml
from pathlib import Path


class TestDomainConfig:
    """Verify domains.yaml loads correctly with all required fields."""

    @pytest.fixture
    def domains(self):
        config_path = Path(__file__).parent.parent / "config" / "domains.yaml"
        assert config_path.exists(), "domains.yaml not found"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_domains_file_loads(self, domains):
        assert domains is not None
        assert isinstance(domains, dict)

    def test_has_expected_domains(self, domains):
        expected = {"business", "financial", "legal", "medical", "technology", "hiring", "strategic", "product", "marketing"}
        domain_keys = set(domains.keys())
        for domain in expected:
            assert domain in domain_keys, f"Missing domain: {domain}"
        assert len(domain_keys) == 9

    def test_list_domains_returns_all(self):
        from config.domain_config import list_domains
        domains = list_domains()
        assert len(domains) == 9
        assert domains == sorted(domains)  # Alphabetically sorted

    def test_each_domain_has_constitutional_overlay(self, domains):
        for name, config in domains.items():
            assert "constitutional_overlay" in config, \
                f"Domain {name} missing constitutional_overlay"

    def test_each_domain_has_evidence_hierarchy(self, domains):
        for name, config in domains.items():
            assert "evidence_hierarchy" in config, \
                f"Domain {name} missing evidence_hierarchy"
            assert isinstance(config["evidence_hierarchy"], list)
            assert len(config["evidence_hierarchy"]) >= 2

    def test_each_domain_has_synthesis_anchors(self, domains):
        for name, config in domains.items():
            assert "synthesis_anchors" in config, \
                f"Domain {name} missing synthesis_anchors"
