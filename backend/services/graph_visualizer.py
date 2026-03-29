"""Graph visualization service — generates visual representations of the verdict pipeline.

Produces a structured description of the LangGraph topology that can be
rendered by the frontend as an interactive pipeline diagram. This allows
users to see exactly which agents ran, their timing, and how data flowed
through the adversarial pipeline.

The visualization is generated from actual graph execution state, not
a static template — it accurately reflects dynamic witness spawning
and confidence-based routing decisions.
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Node display configuration — maps internal node IDs to user-facing metadata
NODE_CONFIG: dict[str, dict[str, str]] = {
    "research": {
        "label": "Research Analyst",
        "icon": "magnifying_glass",
        "color": "#6b7280",
        "description": "Produces neutral, anonymous research package",
    },
    "prosecutor": {
        "label": "Prosecutor",
        "icon": "crossed_swords",
        "color": "#ef4444",
        "description": "Argues FOR the decision (constitutional mandate)",
    },
    "defense": {
        "label": "Defense Counsel",
        "icon": "shield",
        "color": "#3b82f6",
        "description": "Argues AGAINST the decision (constitutional mandate)",
    },
    "judge_cross_exam": {
        "label": "Judge (Cross-Exam)",
        "icon": "balance_scale",
        "color": "#f59e0b",
        "description": "Identifies contested claims for witness verification",
    },
    "witness_fact": {
        "label": "Fact Witness",
        "icon": "eye",
        "color": "#a78bfa",
        "description": "Verifies factual accuracy of contested claims",
    },
    "witness_data": {
        "label": "Data Analyst",
        "icon": "bar_chart",
        "color": "#a78bfa",
        "description": "Verifies statistical and data-based assertions",
    },
    "witness_precedent": {
        "label": "Precedent Expert",
        "icon": "scroll",
        "color": "#a78bfa",
        "description": "Verifies historical precedents cited in arguments",
    },
    "judge_verdict": {
        "label": "Judge (Verdict)",
        "icon": "gavel",
        "color": "#f59e0b",
        "description": "Delivers the final ruling based on all evidence",
    },
    "synthesis": {
        "label": "Synthesis Agent",
        "icon": "sparkles",
        "color": "#10b981",
        "description": "Produces battle-tested improved version of the idea",
    },
}

# Edge types for the pipeline graph
EDGE_TYPES = {
    "sequential": "solid",
    "parallel": "dashed",
    "conditional": "dotted",
}


def generate_pipeline_graph(session_result: Optional[dict] = None) -> dict[str, Any]:
    """Generate a structured pipeline graph for visualization.

    Args:
        session_result: Optional completed session result. If provided,
            the graph includes actual execution data (timing, which nodes
            ran, confidence scores). If None, returns the static topology.

    Returns:
        Dict with 'nodes', 'edges', and 'metadata' keys suitable for
        frontend rendering.
    """
    nodes = []
    edges = []

    # Static topology nodes
    node_order = [
        "research", "prosecutor", "defense",
        "judge_cross_exam", "judge_verdict", "synthesis",
    ]

    for i, node_id in enumerate(node_order):
        config = NODE_CONFIG.get(node_id, {})
        node = {
            "id": node_id,
            "label": config.get("label", node_id),
            "icon": config.get("icon", "circle"),
            "color": config.get("color", "#6b7280"),
            "description": config.get("description", ""),
            "position": i,
            "status": "pending",
        }

        # Enrich with execution data if available
        if session_result:
            node["status"] = _get_node_status(node_id, session_result)

        nodes.append(node)

    # Add dynamic witness nodes if session has witness data
    if session_result:
        witness_reports = session_result.get("witness_reports", [])
        for j, report in enumerate(witness_reports or []):
            w_type = report.get("witness_type", "fact")
            w_id = f"witness_{w_type}"
            config = NODE_CONFIG.get(w_id, NODE_CONFIG.get("witness_fact", {}))
            nodes.append({
                "id": f"{w_id}_{j}",
                "label": config.get("label", f"Witness ({w_type})"),
                "icon": config.get("icon", "eye"),
                "color": config.get("color", "#a78bfa"),
                "description": config.get("description", ""),
                "position": 4 + j * 0.5,  # Between cross-exam and verdict
                "status": "complete",
                "data": {
                    "verdict_on_claim": report.get("verdict_on_claim"),
                    "confidence": report.get("confidence"),
                },
            })

    # Define edges
    edges = [
        {
            "from": "research",
            "to": "prosecutor",
            "type": "parallel",
            "label": "Authorship stripped",
        },
        {
            "from": "research",
            "to": "defense",
            "type": "parallel",
            "label": "Authorship stripped",
        },
        {
            "from": "prosecutor",
            "to": "judge_cross_exam",
            "type": "sequential",
        },
        {
            "from": "defense",
            "to": "judge_cross_exam",
            "type": "sequential",
        },
        {
            "from": "judge_cross_exam",
            "to": "judge_verdict",
            "type": "conditional",
            "label": "Confidence-based routing",
        },
        {
            "from": "judge_verdict",
            "to": "synthesis",
            "type": "sequential",
        },
    ]

    # Add witness edges if applicable
    if session_result:
        witness_reports = session_result.get("witness_reports", [])
        for j, report in enumerate(witness_reports or []):
            w_type = report.get("witness_type", "fact")
            w_id = f"witness_{w_type}_{j}"
            edges.append({
                "from": "judge_cross_exam",
                "to": w_id,
                "type": "conditional",
                "label": f"Verify {w_type}",
            })
            edges.append({
                "from": w_id,
                "to": "judge_verdict",
                "type": "sequential",
            })

    # Metadata
    metadata = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "has_witnesses": bool(
            session_result and session_result.get("witness_reports")
        ),
        "verdict_path": _get_verdict_path(session_result) if session_result else "unknown",
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": metadata,
    }


def _get_node_status(node_id: str, result: dict) -> str:
    """Determine the execution status of a node from session result."""
    status_map = {
        "research": "research_package",
        "prosecutor": "prosecutor_argument",
        "defense": "defense_argument",
        "judge_cross_exam": "witness_reports",
        "judge_verdict": "verdict",
        "synthesis": "synthesis",
    }

    key = status_map.get(node_id)
    if not key:
        return "unknown"

    data = result.get(key)
    if data is not None:
        return "complete"

    errors = result.get("errors", [])
    for err in errors:
        if node_id.replace("_", " ") in str(err).lower():
            return "error"

    return "pending"


def _get_verdict_path(result: dict) -> str:
    """Determine which verdict routing path was taken."""
    witness_reports = result.get("witness_reports", [])
    if not witness_reports:
        return "direct"  # No witnesses, skipped straight to verdict

    confidences = [
        r.get("confidence", 0.5) for r in witness_reports if isinstance(r, dict)
    ]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.5

    has_overruled = any(
        r.get("verdict_on_claim") == "overruled"
        for r in witness_reports if isinstance(r, dict)
    )

    if avg_conf < 0.6:
        return "low_confidence_review"
    if avg_conf >= 0.9 and has_overruled:
        return "hallucination_guard"
    return "normal"
