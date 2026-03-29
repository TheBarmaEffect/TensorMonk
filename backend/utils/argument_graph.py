"""Argument Dependency Graph — models logical relationships between claims.

Builds a directed acyclic graph (DAG) of claim dependencies using keyword
co-occurrence analysis. Claims that share evidence or reference the same
underlying concepts are linked, enabling:

1. **Critical path analysis**: Identify claims that, if overruled, would
   invalidate the most downstream claims (highest out-degree).
2. **Foundation detection**: Claims with zero in-degree are foundational —
   they don't depend on other claims and form the base of the argument.
3. **Vulnerability scoring**: Claims with high in-degree are vulnerable —
   they depend on many other claims being true.
4. **Argument coherence**: A well-structured argument has a connected graph;
   disconnected components suggest disjointed reasoning.

Graph metrics are fed into the Judge's cross-examination to help prioritize
which contested claims would have the highest cascading impact if overruled.

Reference: Toulmin argument model (claim, data, warrant, backing, qualifier, rebuttal)
"""

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class ArgumentGraph:
    """Directed graph of logical dependencies between argument claims.

    Nodes are claim IDs, edges represent logical dependency (claim A's
    evidence supports or references the same concept as claim B).

    The graph is constructed via keyword co-occurrence in claim evidence
    and statements, with a configurable similarity threshold.
    """

    def __init__(self) -> None:
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse: dict[str, set[str]] = defaultdict(set)
        self._node_data: dict[str, dict[str, Any]] = {}

    def add_claim(self, claim_id: str, statement: str, evidence: str, confidence: float) -> None:
        """Register a claim as a node in the graph.

        Args:
            claim_id: Unique claim identifier.
            statement: The claim's assertion text.
            evidence: Supporting evidence text.
            confidence: Stated confidence [0.0-1.0].
        """
        self._node_data[claim_id] = {
            "statement": statement,
            "evidence": evidence,
            "confidence": confidence,
            "keywords": self._extract_keywords(f"{statement} {evidence}"),
        }

    def add_dependency(self, from_id: str, to_id: str) -> None:
        """Add a directed edge: from_id depends on to_id.

        Args:
            from_id: The dependent claim.
            to_id: The claim being depended upon.
        """
        if from_id != to_id and from_id in self._node_data and to_id in self._node_data:
            self._adjacency[to_id].add(from_id)
            self._reverse[from_id].add(to_id)

    def build_from_claims(self, claims: list[dict], similarity_threshold: float = 0.25) -> None:
        """Auto-construct the graph from a list of claims using keyword similarity.

        Two claims are linked if their keyword overlap exceeds the threshold.
        The claim with lower confidence depends on the one with higher confidence,
        modeling the intuition that weaker claims lean on stronger ones.

        Args:
            claims: List of claim dicts with id, statement, evidence, confidence.
            similarity_threshold: Minimum keyword overlap ratio to create an edge.
        """
        # Register all nodes
        for c in claims:
            self.add_claim(
                claim_id=c.get("id", ""),
                statement=c.get("statement", ""),
                evidence=c.get("evidence", ""),
                confidence=c.get("confidence", 0.5),
            )

        # Build edges via keyword co-occurrence
        claim_ids = list(self._node_data.keys())
        for i, id_a in enumerate(claim_ids):
            kw_a = self._node_data[id_a]["keywords"]
            if not kw_a:
                continue

            for id_b in claim_ids[i + 1:]:
                kw_b = self._node_data[id_b]["keywords"]
                if not kw_b:
                    continue

                overlap = kw_a & kw_b
                min_size = min(len(kw_a), len(kw_b))
                similarity = len(overlap) / min_size if min_size > 0 else 0.0

                if similarity >= similarity_threshold:
                    # Lower confidence claim depends on higher confidence claim
                    conf_a = self._node_data[id_a]["confidence"]
                    conf_b = self._node_data[id_b]["confidence"]
                    if conf_a >= conf_b:
                        self.add_dependency(from_id=id_b, to_id=id_a)
                    else:
                        self.add_dependency(from_id=id_a, to_id=id_b)

    def out_degree(self, claim_id: str) -> int:
        """Number of claims that depend on this claim (cascading impact)."""
        return len(self._adjacency.get(claim_id, set()))

    def in_degree(self, claim_id: str) -> int:
        """Number of claims this claim depends on (vulnerability)."""
        return len(self._reverse.get(claim_id, set()))

    @property
    def foundation_claims(self) -> list[str]:
        """Claims with zero in-degree — foundational, independent assertions."""
        return [
            cid for cid in self._node_data
            if self.in_degree(cid) == 0
        ]

    @property
    def critical_claims(self) -> list[str]:
        """Claims with highest out-degree — overruling these has cascading impact."""
        if not self._node_data:
            return []
        max_out = max(self.out_degree(cid) for cid in self._node_data)
        if max_out == 0:
            return []
        return [
            cid for cid in self._node_data
            if self.out_degree(cid) == max_out
        ]

    @property
    def vulnerable_claims(self) -> list[str]:
        """Claims with highest in-degree — most dependent on other claims."""
        if not self._node_data:
            return []
        max_in = max(self.in_degree(cid) for cid in self._node_data)
        if max_in == 0:
            return []
        return [
            cid for cid in self._node_data
            if self.in_degree(cid) == max_in
        ]

    def coherence_score(self) -> float:
        """Measure argument coherence as fraction of nodes in the largest component.

        A fully connected argument graph has coherence 1.0.
        A fully disconnected graph (no edges) has coherence = 1/n.

        Returns:
            Float between 0.0 and 1.0.
        """
        if not self._node_data:
            return 0.0

        # Build undirected adjacency for component detection
        undirected: dict[str, set[str]] = defaultdict(set)
        for src, dsts in self._adjacency.items():
            for dst in dsts:
                undirected[src].add(dst)
                undirected[dst].add(src)

        # BFS to find largest connected component
        visited: set[str] = set()
        largest_component = 0

        for node in self._node_data:
            if node in visited:
                continue
            # BFS from this node
            queue = [node]
            component_size = 0
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component_size += 1
                for neighbor in undirected.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            largest_component = max(largest_component, component_size)

        return round(largest_component / len(self._node_data), 3)

    def cascading_impact(self, claim_id: str) -> int:
        """Count total downstream claims affected if this claim is overruled.

        Uses BFS traversal from the claim through all dependency edges.

        Args:
            claim_id: The claim to evaluate.

        Returns:
            Number of transitively dependent claims.
        """
        if claim_id not in self._node_data:
            return 0

        visited: set[str] = set()
        queue = [claim_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dependent in self._adjacency.get(current, set()):
                if dependent not in visited:
                    queue.append(dependent)

        return len(visited) - 1  # Exclude the claim itself

    def metrics(self) -> dict[str, Any]:
        """Compute comprehensive graph metrics for the argument structure.

        Returns:
            Dict with node count, edge count, coherence, foundations,
            critical claims, and per-claim degree statistics.
        """
        total_edges = sum(len(deps) for deps in self._adjacency.values())

        per_claim = {}
        for cid in self._node_data:
            per_claim[cid] = {
                "out_degree": self.out_degree(cid),
                "in_degree": self.in_degree(cid),
                "cascading_impact": self.cascading_impact(cid),
                "confidence": self._node_data[cid]["confidence"],
                "is_foundation": self.in_degree(cid) == 0,
            }

        result = {
            "node_count": len(self._node_data),
            "edge_count": total_edges,
            "coherence": self.coherence_score(),
            "foundation_claims": self.foundation_claims,
            "critical_claims": self.critical_claims,
            "vulnerable_claims": self.vulnerable_claims,
            "per_claim": per_claim,
        }

        logger.info(
            "Argument graph: %d nodes, %d edges, coherence=%.3f, "
            "%d foundations, %d critical",
            result["node_count"], result["edge_count"], result["coherence"],
            len(result["foundation_claims"]), len(result["critical_claims"]),
        )

        return result

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """Extract significant keywords from text for similarity analysis.

        Filters out short words (≤3 chars) which are typically articles,
        prepositions, and conjunctions.

        Args:
            text: Input text to extract keywords from.

        Returns:
            Set of lowercase significant words.
        """
        return {w.lower() for w in text.split() if len(w) > 3}


def build_argument_graphs(
    prosecutor_claims: list[dict],
    defense_claims: list[dict],
) -> dict[str, Any]:
    """Build separate argument graphs for prosecution and defense.

    Constructs a DAG for each side and computes comparative metrics,
    giving the Judge quantitative insight into argument structure quality.

    Args:
        prosecutor_claims: List of prosecution claim dicts.
        defense_claims: List of defense claim dicts.

    Returns:
        Dict with per-side metrics and comparative analysis.
    """
    pro_graph = ArgumentGraph()
    pro_graph.build_from_claims(prosecutor_claims)

    def_graph = ArgumentGraph()
    def_graph.build_from_claims(defense_claims)

    pro_metrics = pro_graph.metrics()
    def_metrics = def_graph.metrics()

    return {
        "prosecution": pro_metrics,
        "defense": def_metrics,
        "comparative": {
            "coherence_differential": round(
                pro_metrics["coherence"] - def_metrics["coherence"], 3
            ),
            "pro_foundations": len(pro_metrics["foundation_claims"]),
            "def_foundations": len(def_metrics["foundation_claims"]),
            "pro_has_critical_path": len(pro_metrics["critical_claims"]) > 0,
            "def_has_critical_path": len(def_metrics["critical_claims"]) > 0,
        },
    }
