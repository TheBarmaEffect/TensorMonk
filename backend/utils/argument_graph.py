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
import math
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# Common English stop words filtered from TF-IDF to reduce noise
_STOP_WORDS = frozenset({
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "have", "been", "will", "more",
    "when", "who", "what", "where", "which", "their", "this", "that", "with",
    "from", "they", "would", "there", "than", "been", "could", "them", "some",
    "into", "only", "come", "over", "such", "also", "most", "should", "about",
})


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

    def build_from_claims(self, claims: list[dict], similarity_threshold: float = 0.25, use_tfidf: bool = False) -> None:
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

        # Build edges via keyword similarity (raw overlap or TF-IDF cosine)
        claim_ids = list(self._node_data.keys())
        for i, id_a in enumerate(claim_ids):
            kw_a = self._node_data[id_a]["keywords"]
            if not kw_a:
                continue

            for id_b in claim_ids[i + 1:]:
                kw_b = self._node_data[id_b]["keywords"]
                if not kw_b:
                    continue

                if use_tfidf:
                    similarity = self.compute_tfidf_similarity(id_a, id_b)
                else:
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
            "topological_order": self.topological_sort(),
            "per_claim": per_claim,
        }

        logger.info(
            "Argument graph: %d nodes, %d edges, coherence=%.3f, "
            "%d foundations, %d critical",
            result["node_count"], result["edge_count"], result["coherence"],
            len(result["foundation_claims"]), len(result["critical_claims"]),
        )

        return result

    def topological_sort(self) -> list[str]:
        """Return claims in dependency order (foundations first, dependents last).

        Uses Kahn's algorithm for topological sorting of the DAG.
        Claims with no dependencies appear first; claims that depend on
        many others appear last. This ordering is useful for understanding
        the logical build-up of an argument.

        Returns:
            List of claim IDs in topological order, or empty if cycle detected.
        """
        if not self._node_data:
            return []

        in_degree: dict[str, int] = {cid: 0 for cid in self._node_data}
        for src, dsts in self._adjacency.items():
            for dst in dsts:
                if dst in in_degree:
                    in_degree[dst] += 1

        # Start with zero in-degree nodes (foundations)
        queue = [cid for cid, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dependent in self._adjacency.get(node, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(result) != len(self._node_data):
            logger.warning("Cycle detected in argument graph — topological sort incomplete")
            return []

        return result

    def compute_tfidf_similarity(self, id_a: str, id_b: str) -> float:
        """Compute TF-IDF weighted cosine similarity between two claims.

        Standard TF-IDF: term frequency is normalized by document length,
        inverse document frequency uses log(N/df) where N is total claims
        and df is the number of claims containing the term.

        This produces more accurate similarity than raw keyword overlap because
        common words (appearing in many claims) are down-weighted while
        distinctive terms that truly indicate logical dependency are up-weighted.

        Args:
            id_a: First claim ID.
            id_b: Second claim ID.

        Returns:
            Cosine similarity in [0.0, 1.0].
        """
        if id_a not in self._node_data or id_b not in self._node_data:
            return 0.0

        kw_a = self._node_data[id_a]["keywords"]
        kw_b = self._node_data[id_b]["keywords"]
        all_terms = kw_a | kw_b
        if not all_terms:
            return 0.0

        # Compute IDF for each term across all claims
        n_docs = len(self._node_data)
        if n_docs <= 1:
            return 0.0

        doc_freq: dict[str, int] = defaultdict(int)
        for cid in self._node_data:
            for term in self._node_data[cid]["keywords"]:
                doc_freq[term] += 1

        # TF-IDF vectors
        def _tfidf_vector(claim_keywords: set[str]) -> dict[str, float]:
            vec: dict[str, float] = {}
            n_terms = len(claim_keywords) if claim_keywords else 1
            for term in claim_keywords:
                tf = 1.0 / n_terms  # Normalized TF
                # Smooth IDF: log(1 + N/df) avoids zero for terms in all docs
                idf = math.log(1.0 + n_docs / (1 + doc_freq.get(term, 0)))
                vec[term] = tf * idf
            return vec

        vec_a = _tfidf_vector(kw_a)
        vec_b = _tfidf_vector(kw_b)

        # Cosine similarity
        dot = sum(vec_a.get(t, 0) * vec_b.get(t, 0) for t in all_terms)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values())) or 1e-10
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values())) or 1e-10

        return dot / (mag_a * mag_b)

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """Extract significant keywords from text for similarity analysis.

        Filters out short words (≤3 chars) and common English stop words
        to retain only meaningful content terms for similarity computation.

        Args:
            text: Input text to extract keywords from.

        Returns:
            Set of lowercase significant words.
        """
        return {
            w.lower() for w in text.split()
            if len(w) > 3 and w.lower() not in _STOP_WORDS
        }


class CrossGraphAnalyzer:
    """Analyzes dependencies BETWEEN prosecution and defense argument graphs.

    While each side's internal graph captures logical dependencies within
    an argument, the cross-graph analysis identifies claims from opposing
    sides that reference the same underlying facts. This reveals:

    1. **Shared evidence claims**: Both sides citing the same data for
       opposite conclusions — the most contested factual territory.
    2. **Contradictory foundations**: Foundation claims on one side that
       directly conflict with foundation claims on the other.
    3. **Asymmetric vulnerability**: Claims on one side that depend on
       facts the other side attacks — structural weakness.

    This analysis feeds into cross-examination to help the Judge identify
    the most productive lines of questioning.
    """

    def __init__(self, pro_graph: ArgumentGraph, def_graph: ArgumentGraph):
        self.pro = pro_graph
        self.defense = def_graph

    def find_shared_evidence(self, similarity_threshold: float = 0.3) -> list[dict[str, Any]]:
        """Find pairs of opposing claims that reference the same underlying facts.

        Uses TF-IDF cosine similarity between cross-graph claim pairs to
        identify shared evidence territory.

        Args:
            similarity_threshold: Minimum similarity to consider claims related.

        Returns:
            List of dicts with pro_claim, def_claim, similarity, and type.
        """
        # Create a combined temporary graph for TF-IDF computation across both sides
        combined = ArgumentGraph()
        for cid, data in self.pro._node_data.items():
            combined.add_claim(
                f"pro_{cid}", data["statement"],
                data["evidence"], data["confidence"],
            )
        for cid, data in self.defense._node_data.items():
            combined.add_claim(
                f"def_{cid}", data["statement"],
                data["evidence"], data["confidence"],
            )

        shared_pairs: list[dict[str, Any]] = []
        for pro_cid in self.pro._node_data:
            for def_cid in self.defense._node_data:
                sim = combined.compute_tfidf_similarity(f"pro_{pro_cid}", f"def_{def_cid}")
                if sim >= similarity_threshold:
                    pro_is_foundation = self.pro.in_degree(pro_cid) == 0
                    def_is_foundation = self.defense.in_degree(def_cid) == 0

                    pair_type = "contested_territory"
                    if pro_is_foundation and def_is_foundation:
                        pair_type = "contradictory_foundations"
                    elif pro_is_foundation or def_is_foundation:
                        pair_type = "foundation_attack"

                    shared_pairs.append({
                        "pro_claim": pro_cid,
                        "def_claim": def_cid,
                        "similarity": round(sim, 4),
                        "type": pair_type,
                        "pro_confidence": self.pro._node_data[pro_cid]["confidence"],
                        "def_confidence": self.defense._node_data[def_cid]["confidence"],
                    })

        # Sort by similarity (highest first)
        shared_pairs.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(
            "Cross-graph analysis: %d shared evidence pairs found "
            "(%d contradictory foundations)",
            len(shared_pairs),
            sum(1 for p in shared_pairs if p["type"] == "contradictory_foundations"),
        )

        return shared_pairs

    def analyze(self) -> dict[str, Any]:
        """Run full cross-graph analysis.

        Returns:
            Dict with shared evidence pairs and structural summary.
        """
        shared = self.find_shared_evidence()

        types_count: dict[str, int] = {}
        for pair in shared:
            types_count[pair["type"]] = types_count.get(pair["type"], 0) + 1

        return {
            "shared_evidence_pairs": shared,
            "pair_count": len(shared),
            "types": types_count,
            "has_contradictory_foundations": types_count.get("contradictory_foundations", 0) > 0,
        }


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

    # Cross-graph analysis: find claims from opposing sides that reference
    # the same underlying facts — the most contested factual territory.
    cross_analyzer = CrossGraphAnalyzer(pro_graph, def_graph)
    cross_analysis = cross_analyzer.analyze()

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
        "cross_graph": cross_analysis,
    }
