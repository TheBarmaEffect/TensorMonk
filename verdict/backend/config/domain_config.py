"""Domain configuration loader — reads constitutional overlays from YAML at runtime.

The YAML config defines per-domain:
  - constitutional_overlay: additional prompt constraints for adversarial agents
  - evidence_hierarchy: ordered list of evidence types by authority
  - suggested_format: default output format for this domain
  - synthesis_anchors: few-shot examples for synthesis output
"""

import os
import logging
from functools import lru_cache
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

DOMAINS_YAML_PATH = os.path.join(os.path.dirname(__file__), "domains.yaml")


@lru_cache(maxsize=1)
def _load_domains() -> dict:
    """Load and cache the domain configuration from YAML."""
    try:
        with open(DOMAINS_YAML_PATH, "r") as f:
            config = yaml.safe_load(f)
        logger.info("Loaded domain config with %d domains", len(config))
        return config
    except FileNotFoundError:
        logger.warning("domains.yaml not found at %s, using empty config", DOMAINS_YAML_PATH)
        return {}
    except yaml.YAMLError as e:
        logger.error("Failed to parse domains.yaml: %s", e)
        return {}


def get_domain_config(domain: str) -> dict:
    """Get the full configuration for a specific domain.

    Returns a dict with keys: constitutional_overlay, evidence_hierarchy,
    suggested_format, synthesis_anchors. Falls back to empty strings/lists
    if the domain is not configured.
    """
    domains = _load_domains()
    config = domains.get(domain, {})
    return {
        "constitutional_overlay": config.get("constitutional_overlay", ""),
        "evidence_hierarchy": config.get("evidence_hierarchy", []),
        "suggested_format": config.get("suggested_format", "executive"),
        "synthesis_anchors": config.get("synthesis_anchors", []),
    }


def get_constitutional_overlay(domain: str) -> str:
    """Get just the constitutional overlay string for a domain."""
    return get_domain_config(domain).get("constitutional_overlay", "")


def get_evidence_hierarchy(domain: str) -> list[str]:
    """Get the evidence hierarchy for a domain, ordered by authority."""
    return get_domain_config(domain).get("evidence_hierarchy", [])


def get_synthesis_anchors(domain: str) -> list[str]:
    """Get few-shot synthesis anchors for domain-specific tool/action examples."""
    return get_domain_config(domain).get("synthesis_anchors", [])


def get_suggested_format(domain: str) -> str:
    """Get the suggested output format for a domain."""
    return get_domain_config(domain).get("suggested_format", "executive")


def list_domains() -> list[str]:
    """Return all configured domain names, sorted alphabetically."""
    return sorted(_load_domains().keys())
