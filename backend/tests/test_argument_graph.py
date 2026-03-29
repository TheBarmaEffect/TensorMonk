"""Tests for argument dependency graph — DAG construction and graph-theoretic metrics."""

import pytest
from utils.argument_graph import ArgumentGraph, CrossGraphAnalyzer, build_argument_graphs


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

    def test_filters_stop_words(self):
        kw = ArgumentGraph._extract_keywords("this should also have been there with from")
        assert "this" not in kw
        assert "should" not in kw
        assert "also" not in kw
        assert "have" not in kw


class TestTopologicalSort:
    """Test Kahn's algorithm topological sorting."""

    def test_empty_graph(self):
        g = ArgumentGraph()
        assert g.topological_sort() == []

    def test_single_node(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        assert g.topological_sort() == ["c1"]

    def test_linear_chain(self):
        g = ArgumentGraph()
        g.add_claim("c1", "Foundation", "ev", 0.9)
        g.add_claim("c2", "Middle", "ev", 0.7)
        g.add_claim("c3", "Conclusion", "ev", 0.5)
        g.add_dependency("c2", "c1")  # c2 depends on c1
        g.add_dependency("c3", "c2")  # c3 depends on c2
        order = g.topological_sort()
        assert order.index("c1") < order.index("c2")
        assert order.index("c2") < order.index("c3")

    def test_foundations_come_first(self):
        g = ArgumentGraph()
        g.add_claim("c1", "Base", "ev", 0.9)
        g.add_claim("c2", "Derived", "ev", 0.7)
        g.add_claim("c3", "Also derived", "ev", 0.6)
        g.add_dependency("c2", "c1")
        g.add_dependency("c3", "c1")
        order = g.topological_sort()
        assert order[0] == "c1"  # Foundation first

    def test_included_in_metrics(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.9)
        g.add_claim("c2", "B", "ev", 0.7)
        g.add_dependency("c2", "c1")
        m = g.metrics()
        assert "topological_order" in m
        assert len(m["topological_order"]) == 2


class TestTFIDFSimilarity:
    """Test TF-IDF weighted cosine similarity."""

    def test_identical_claims_high_similarity(self):
        g = ArgumentGraph()
        g.add_claim("c1", "market growth opportunity revenue", "data shows growth", 0.8)
        g.add_claim("c2", "market growth opportunity revenue", "data shows growth", 0.7)
        sim = g.compute_tfidf_similarity("c1", "c2")
        assert sim > 0.8

    def test_different_claims_low_similarity(self):
        g = ArgumentGraph()
        g.add_claim("c1", "market growth opportunity revenue", "financial data", 0.8)
        g.add_claim("c2", "legal compliance regulation framework", "policy review", 0.7)
        sim = g.compute_tfidf_similarity("c1", "c2")
        assert sim < 0.3

    def test_nonexistent_claim_returns_zero(self):
        g = ArgumentGraph()
        g.add_claim("c1", "A", "ev", 0.8)
        assert g.compute_tfidf_similarity("c1", "nonexistent") == 0.0

    def test_tfidf_similarity_bounded(self):
        g = ArgumentGraph()
        g.add_claim("c1", "market growth", "data", 0.8)
        g.add_claim("c2", "market decline", "stats", 0.7)
        sim = g.compute_tfidf_similarity("c1", "c2")
        assert 0.0 <= sim <= 1.0

    def test_build_from_claims_with_tfidf(self):
        g = ArgumentGraph()
        claims = [
            {"id": "c1", "statement": "market growth revenue increase profit", "evidence": "financial data shows 20% market expansion revenue", "confidence": 0.9},
            {"id": "c2", "statement": "market growth revenue expansion profit", "evidence": "quarterly reports show market growth revenue trends", "confidence": 0.7},
            {"id": "c3", "statement": "legal compliance regulation framework policy", "evidence": "government policy framework regulatory analysis", "confidence": 0.8},
        ]
        g.build_from_claims(claims, use_tfidf=True, similarity_threshold=0.1)
        # c1 and c2 share many keywords (market, growth, revenue) — should be linked
        has_edge = (g.out_degree("c1") > 0 or g.out_degree("c2") > 0
                    or g.in_degree("c1") > 0 or g.in_degree("c2") > 0)
        assert has_edge


class TestCrossGraphAnalysis:
    """Test cross-graph dependency analysis between prosecution and defense."""

    def test_no_shared_evidence(self):
        pro = ArgumentGraph()
        pro.add_claim("p1", "market growth opportunity", "revenue data", 0.8)
        defense = ArgumentGraph()
        defense.add_claim("d1", "legal compliance regulation", "policy framework", 0.7)
        analyzer = CrossGraphAnalyzer(pro, defense)
        shared = analyzer.find_shared_evidence()
        assert len(shared) == 0

    def test_shared_evidence_detected(self):
        pro = ArgumentGraph()
        pro.add_claim("p1", "market revenue growth profit expansion", "financial data shows revenue", 0.8)
        defense = ArgumentGraph()
        defense.add_claim("d1", "market revenue decline profit shrinking", "financial data shows revenue", 0.7)
        analyzer = CrossGraphAnalyzer(pro, defense)
        shared = analyzer.find_shared_evidence(similarity_threshold=0.1)
        assert len(shared) >= 1
        assert shared[0]["pro_claim"] == "p1"
        assert shared[0]["def_claim"] == "d1"

    def test_contradictory_foundations_type(self):
        pro = ArgumentGraph()
        pro.add_claim("p1", "market revenue growth profit expansion", "financial data", 0.8)
        defense = ArgumentGraph()
        defense.add_claim("d1", "market revenue decline profit contraction", "financial data", 0.7)
        analyzer = CrossGraphAnalyzer(pro, defense)
        shared = analyzer.find_shared_evidence(similarity_threshold=0.1)
        if shared:
            # Both are foundations (zero in-degree), so type should be contradictory_foundations
            assert shared[0]["type"] == "contradictory_foundations"

    def test_analyze_returns_full_structure(self):
        pro = ArgumentGraph()
        pro.add_claim("p1", "test claim", "evidence", 0.8)
        defense = ArgumentGraph()
        defense.add_claim("d1", "test claim", "evidence", 0.7)
        analyzer = CrossGraphAnalyzer(pro, defense)
        result = analyzer.analyze()
        assert "shared_evidence_pairs" in result
        assert "pair_count" in result
        assert "types" in result
        assert "has_contradictory_foundations" in result

    def test_build_argument_graphs_includes_cross_graph(self):
        pro = [
            {"id": "p1", "statement": "Market opportunity", "evidence": "data", "confidence": 0.85},
        ]
        defense = [
            {"id": "d1", "statement": "Competition fierce", "evidence": "analysis", "confidence": 0.75},
        ]
        result = build_argument_graphs(pro, defense)
        assert "cross_graph" in result
        assert "pair_count" in result["cross_graph"]
