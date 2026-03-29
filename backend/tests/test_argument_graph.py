"""Tests for argument dependency graph — DAG construction and graph-theoretic metrics."""

import pytest
from utils.argument_graph import ArgumentGraph, build_argument_graphs


class TestArgumentGraphConstruction:
    """Test DAG construction from claims."""

    def test_add_single_claim(self):
        g = ArgumentGraph()
        g.add_claim("c1", "Market is growing", "Revenue data shows 20% YoY", 0.8)
        assert "c1" in g._node_data
        assert g._node_data["c1"]["confidence"] == 0.8

    def test_add_dependency(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        assert "c2" in g._adjacency["c1"]
        assert "c1" in g._reverse["c2"]

    def test_no_self_dependency(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.8)
        g.add_dependency("c1", "c1")
        assert g.out_degree("c1") == 0

    def test_build_from_claims_creates_edges(self):
        claims = [
            {"id": "c1", "statement": "Market growth strong demand", "evidence": "Revenue data", "confidence": 0.9},
            {"id": "c2", "statement": "Strong market demand growth", "evidence": "Survey data", "confidence": 0.7},
        ]
        g = ArgumentGraph()
        g.build_from_claims(claims, similarity_threshold=0.3)
        # Should create a dependency edge (c2 depends on c1 because c1 has higher confidence)
        total_edges = sum(len(deps) for deps in g._adjacency.values())
        assert total_edges >= 1

    def test_no_edges_for_unrelated_claims(self):
        claims = [
            {"id": "c1", "statement": "Revenue increased dramatically", "evidence": "Financial data", "confidence": 0.9},
            {"id": "c2", "statement": "Technical infrastructure robust", "evidence": "Architecture review", "confidence": 0.8},
        ]
        g = ArgumentGraph()
        g.build_from_claims(claims, similarity_threshold=0.5)
        total_edges = sum(len(deps) for deps in g._adjacency.values())
        assert total_edges == 0


class TestGraphMetrics:
    """Test graph-theoretic metric computation."""

    def test_out_degree(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_claim("c3", "C", "ev", 0.6)
        g.add_dependency("c2", "c1")
        g.add_dependency("c3", "c1")
        assert g.out_degree("c1") == 2
        assert g.out_degree("c2") == 0

    def test_in_degree(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        assert g.in_degree("c2") == 1
        assert g.in_degree("c1") == 0

    def test_foundation_claims(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        foundations = g.foundation_claims
        assert "c1" in foundations
        assert "c2" not in foundations

    def test_critical_claims(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_claim("c3", "C", "ev", 0.6)
        g.add_dependency("c2", "c1")
        g.add_dependency("c3", "c1")
        critical = g.critical_claims
        assert "c1" in critical

    def test_vulnerable_claims(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.8)
        g.add_claim("c3", "C", "ev", 0.5)
        g.add_dependency("c3", "c1")
        g.add_dependency("c3", "c2")
        vulnerable = g.vulnerable_claims
        assert "c3" in vulnerable

    def test_coherence_score_connected(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        assert g.coherence_score() == 1.0

    def test_coherence_score_disconnected(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        # No edges = each node is its own component
        assert g.coherence_score() == 0.5

    def test_coherence_score_empty(self):
        g = ArgumentGraph()
        assert g.coherence_score() == 0.0

    def test_cascading_impact(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_claim("c3", "C", "ev", 0.5)
        g.add_dependency("c2", "c1")  # c2 depends on c1
        g.add_dependency("c3", "c2")  # c3 depends on c2
        # Overruling c1 cascades to c2 and c3
        assert g.cascading_impact("c1") == 2

    def test_cascading_impact_leaf(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        assert g.cascading_impact("c2") == 0

    def test_metrics_returns_complete_data(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        m = g.metrics()
        assert m["node_count"] == 2
        assert m["edge_count"] == 1
        assert "foundation_claims" in m
        assert "critical_claims" in m
        assert "per_claim" in m
        assert "c1" in m["per_claim"]


class TestBuildArgumentGraphs:
    """Test the comparative graph builder."""

    def test_builds_both_graphs(self):
        pro = [
            {"id": "p1", "statement": "Market opportunity large", "evidence": "data", "confidence": 0.85},
            {"id": "p2", "statement": "Technology ready deploy", "evidence": "tests", "confidence": 0.8},
        ]
        defense = [
            {"id": "d1", "statement": "Competition intense fierce", "evidence": "analysis", "confidence": 0.75},
            {"id": "d2", "statement": "Costs prohibitively high", "evidence": "budget", "confidence": 0.7},
        ]
        result = build_argument_graphs(pro, defense)
        assert "prosecution" in result
        assert "defense" in result
        assert "comparative" in result
        assert result["prosecution"]["node_count"] == 2
        assert result["defense"]["node_count"] == 2

    def test_comparative_metrics(self):
        pro = [{"id": "p1", "statement": "A", "evidence": "ev", "confidence": 0.9}]
        defense = [{"id": "d1", "statement": "B", "evidence": "ev", "confidence": 0.8}]
        result = build_argument_graphs(pro, defense)
        assert "coherence_differential" in result["comparative"]
        assert "pro_foundations" in result["comparative"]

    def test_empty_claims(self):
        result = build_argument_graphs([], [])
        assert result["prosecution"]["node_count"] == 0
        assert result["defense"]["node_count"] == 0


class TestKeywordExtraction:
    """Test the keyword extraction utility."""

    def test_filters_short_words(self):
        kw = ArgumentGraph._extract_keywords("the cat is on a mat")
        assert "the" not in kw
        assert "is" not in kw
        assert "on" not in kw

    def test_preserves_significant_words(self):
        kw = ArgumentGraph._extract_keywords("market growth opportunity revenue")
        assert "market" in kw
        assert "growth" in kw
        assert "opportunity" in kw
        assert "revenue" in kw

    def test_lowercase(self):
        kw = ArgumentGraph._extract_keywords("Market GROWTH Revenue")
        assert "market" in kw
        assert "growth" in kw

    def test_empty_string(self):
        kw = ArgumentGraph._extract_keywords("")
        assert len(kw) == 0
