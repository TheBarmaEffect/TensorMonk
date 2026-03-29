"""Tests for the graph visualization service."""

import pytest
from services.graph_visualizer import (
    generate_pipeline_graph,
    NODE_CONFIG,
    _get_node_status,
    _get_verdict_path,
)


class TestStaticTopology:
    """Test the static pipeline graph without session data."""

    def test_returns_nodes_and_edges(self):
        graph = generate_pipeline_graph()
        assert "nodes" in graph
        assert "edges" in graph
        assert "metadata" in graph

    def test_has_all_core_nodes(self):
        graph = generate_pipeline_graph()
        node_ids = {n["id"] for n in graph["nodes"]}
        assert "research" in node_ids
        assert "prosecutor" in node_ids
        assert "defense" in node_ids
        assert "judge_cross_exam" in node_ids
        assert "judge_verdict" in node_ids
        assert "synthesis" in node_ids

    def test_nodes_have_required_fields(self):
        graph = generate_pipeline_graph()
        for node in graph["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "color" in node
            assert "status" in node

    def test_edges_connect_valid_nodes(self):
        graph = generate_pipeline_graph()
        node_ids = {n["id"] for n in graph["nodes"]}
        for edge in graph["edges"]:
            assert edge["from"] in node_ids
            assert edge["to"] in node_ids

    def test_has_parallel_edges_for_arguments(self):
        graph = generate_pipeline_graph()
        parallel_edges = [e for e in graph["edges"] if e.get("type") == "parallel"]
        assert len(parallel_edges) == 2  # research→prosecutor, research→defense

    def test_metadata_has_expected_fields(self):
        graph = generate_pipeline_graph()
        meta = graph["metadata"]
        assert "total_nodes" in meta
        assert "total_edges" in meta
        assert meta["total_nodes"] == 6  # Core nodes only


class TestSessionGraph:
    """Test graph with session execution data."""

    @pytest.fixture
    def complete_result(self):
        return {
            "research_package": {"summary": "test"},
            "prosecutor_argument": {"opening": "test", "claims": []},
            "defense_argument": {"opening": "test", "claims": []},
            "witness_reports": [
                {
                    "witness_type": "fact",
                    "verdict_on_claim": "sustained",
                    "confidence": 0.85,
                    "resolution": "Verified",
                },
                {
                    "witness_type": "data",
                    "verdict_on_claim": "overruled",
                    "confidence": 0.7,
                    "resolution": "Disputed",
                },
            ],
            "verdict": {"ruling": "conditional", "confidence": 0.75},
            "synthesis": {"improved_idea": "Better version"},
            "errors": [],
        }

    def test_includes_witness_nodes(self, complete_result):
        graph = generate_pipeline_graph(complete_result)
        witness_nodes = [n for n in graph["nodes"] if "witness" in n["id"]]
        assert len(witness_nodes) == 2

    def test_witness_nodes_have_data(self, complete_result):
        graph = generate_pipeline_graph(complete_result)
        witness_nodes = [n for n in graph["nodes"] if "witness" in n["id"]]
        for w in witness_nodes:
            assert "data" in w
            assert "verdict_on_claim" in w["data"]
            assert "confidence" in w["data"]

    def test_complete_nodes_have_status(self, complete_result):
        graph = generate_pipeline_graph(complete_result)
        for node in graph["nodes"]:
            if "witness" not in node["id"]:
                assert node["status"] == "complete"

    def test_metadata_reflects_witnesses(self, complete_result):
        graph = generate_pipeline_graph(complete_result)
        assert graph["metadata"]["has_witnesses"] is True

    def test_verdict_path_detection(self, complete_result):
        path = _get_verdict_path(complete_result)
        assert path in ("normal", "low_confidence_review", "hallucination_guard", "direct")


class TestVerdictPathDetection:
    """Test confidence-based verdict path classification."""

    def test_direct_path_no_witnesses(self):
        assert _get_verdict_path({"witness_reports": []}) == "direct"
        assert _get_verdict_path({}) == "direct"

    def test_normal_path(self):
        result = {
            "witness_reports": [
                {"confidence": 0.75, "verdict_on_claim": "sustained"},
            ]
        }
        assert _get_verdict_path(result) == "normal"

    def test_low_confidence_review_path(self):
        result = {
            "witness_reports": [
                {"confidence": 0.3, "verdict_on_claim": "inconclusive"},
                {"confidence": 0.4, "verdict_on_claim": "inconclusive"},
            ]
        }
        assert _get_verdict_path(result) == "low_confidence_review"

    def test_hallucination_guard_path(self):
        result = {
            "witness_reports": [
                {"confidence": 0.95, "verdict_on_claim": "overruled"},
            ]
        }
        assert _get_verdict_path(result) == "hallucination_guard"


class TestNodeConfig:
    """Verify node configuration completeness."""

    def test_all_nodes_have_labels(self):
        for node_id, config in NODE_CONFIG.items():
            assert "label" in config, f"Missing label for {node_id}"
            assert "color" in config, f"Missing color for {node_id}"
            assert "description" in config, f"Missing description for {node_id}"

    def test_adversarial_agents_have_distinct_colors(self):
        pro_color = NODE_CONFIG["prosecutor"]["color"]
        def_color = NODE_CONFIG["defense"]["color"]
        assert pro_color != def_color
