"""LangGraph StateGraph for the Verdict adversarial courtroom pipeline.

Graph topology:
  input → research → [prosecutor, defense] (parallel) → judge_cross_exam
  → should_spawn_witnesses (conditional) → witness_nodes (parallel)
  → confidence_gate (conditional) → judge_verdict → synthesis → END

Checkpointing: Uses AsyncRedisSaver when REDIS_URL is set, falling back to
MemorySaver for local development. Redis provides fault-tolerant persistence
across process restarts and horizontal scaling.

interrupt_before: The graph supports pausing before the 'verdict' node when
witness confidence is below threshold, allowing human review before ruling.
"""

import asyncio
import logging
import os
from typing import TypedDict, Optional, Annotated, Callable
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Redis-backed checkpointer for production fault tolerance — falls back to
# in-memory MemorySaver when Redis is unavailable or not configured.
try:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

from agents.research import ResearchAgent
from agents.prosecutor import ProsecutorAgent
from agents.defense import DefenseAgent
from agents.judge import JudgeAgent
from agents.witness import WitnessAgent
from agents.synthesis import SynthesisAgent
from models.schemas import StreamEvent
from config.domain_config import get_constitutional_overlay, get_evidence_hierarchy
from utils.event_bus import pipeline_event_bus, PipelineEvent, EventPriority
from utils.metrics import pipeline_metrics
from utils.confidence_calibration import calibration_tracker
from utils.argument_graph import build_argument_graphs
from utils.verdict_stability import full_stability_analysis
from utils.argument_quality import score_argument_quality
from utils.validators import validate_research_package


def strip_authorship(research_package: dict) -> dict:
    """Enforce authorship blindness — borrowed from double-blind peer review.

    Strips all identifying metadata from the research package before it reaches
    the adversarial agents (Prosecutor and Defense). Neither agent can determine
    who authored the research or adjust their argumentation strategy based on
    source credibility. This is a core architectural constraint that ensures
    genuine adversarial tension: arguments must stand on evidence alone.

    Stripped fields: agent_id, agent, source, model, timestamp, metadata, author,
    provider, version, run_id, trace_id.
    """
    if not research_package:
        return {}
    blind_copy = dict(research_package)
    _AUTHORSHIP_FIELDS = (
        "agent_id", "agent", "source", "model", "timestamp",
        "metadata", "author", "provider", "version", "run_id", "trace_id",
    )
    stripped_count = 0
    for meta_key in _AUTHORSHIP_FIELDS:
        if meta_key in blind_copy:
            blind_copy.pop(meta_key)
            stripped_count += 1
    if stripped_count > 0:
        logger.info("Authorship blindness: stripped %d identifying fields from research package", stripped_count)
    return blind_copy

logger = logging.getLogger(__name__)

# Module-level callback registry — stores stream_callback functions keyed by
# thread_id so they don't enter the serializable LangGraph state. This avoids
# "Type is not msgpack serializable: function" errors from the checkpointer.
_callback_registry: dict[str, Callable] = {}


class VerdictState(TypedDict):
    """The shared state flowing through the verdict graph.

    Fields are immutable between nodes — each node returns a partial update.
    Adversarial isolation is maintained by the graph: prosecutor_node and
    defense_node receive only the research_package, never each other's output.
    The judge receives both arguments only after both are complete.

    Intelligence pipeline: quality scores and structural analysis computed in
    earlier nodes flow downstream to inform routing, witness prioritization,
    and synthesis focus — not just emitted as telemetry.
    """

    decision: dict
    output_format: str                     # executive | technical | legal | investor
    domain: str                            # auto-detected domain (business, legal, etc.)
    research_package: Optional[dict]
    prosecutor_argument: Optional[dict]
    defense_argument: Optional[dict]
    argument_quality: Optional[dict]       # quality grades from parallel_arguments_node
    argument_graphs: Optional[dict]        # structural DAG analysis from cross_exam_node
    contested_claims: Optional[list]
    witness_reports: Optional[list]
    cross_examination: Optional[dict]
    verdict: Optional[dict]
    verdict_stability: Optional[dict]      # stability analysis from verdict node
    synthesis: Optional[dict]
    thread_id: str
    errors: Annotated[list, operator.add]


# ── Node functions ──────────────────────────────────────────────────────────


async def research_node(state: VerdictState) -> dict:
    """Run the Research agent to produce a neutral research package.

    The research package is the ONLY shared context between prosecutor and
    defense — authorship is anonymous (neither agent knows who wrote it).
    """
    agent = ResearchAgent()
    decision = state["decision"]
    callback = _callback_registry.get(state.get("thread_id", ""))
    output_format = state.get("output_format", "executive")
    domain = state.get("domain", "business")
    tid = state.get("thread_id", "")

    with pipeline_metrics.track("research"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.research.start", session_id=tid,
            ))
            package = await agent.run(
                decision_question=decision["question"],
                context=decision.get("context"),
                output_format=output_format,
                domain=domain,
                stream_callback=callback,
            )
            # Validate research completeness before passing to adversarial agents
            is_complete, missing = validate_research_package(package)
            if not is_complete:
                logger.warning("Research package incomplete — missing: %s", missing)

            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.research.complete", session_id=tid,
                payload={
                    "quality": package.get("_quality_scores", {}).get("overall", 0),
                    "is_complete": is_complete,
                    "missing_fields": missing,
                },
            ))
            return {"research_package": package}
        except Exception as e:
            logger.error("Research node failed: %s", e)
            return {"research_package": {}, "errors": [f"Research: {str(e)}"]}


def _validate_constitutional_compliance(
    argument_data: dict,
    expected_side: str,
) -> dict:
    """Validate that an argument complies with its constitutional directive.

    Checks that the prosecution actually argues FOR and defense argues AGAINST.
    Uses sentiment analysis heuristics on the opening statement to detect
    directive violations (e.g., a prosecutor that argues against the decision).

    This is a pipeline quality gate — violations are logged as warnings and
    included in event bus telemetry, but do not block execution (the adversarial
    process still benefits from the argument content).

    Args:
        argument_data: The serialized argument dict.
        expected_side: Either "prosecutor" (must argue FOR) or "defense" (must argue AGAINST).

    Returns:
        Dict with compliance assessment: compliant (bool), violations (list), confidence.
    """
    if not argument_data:
        return {"compliant": False, "violations": ["No argument data"], "confidence": 0.0}

    opening = (argument_data.get("opening") or "").lower()
    violations = []

    # Prosecutor must argue FOR — check for hedging/negative language
    pro_negative_signals = ("should not", "shouldn't", "against", "reject", "fail", "risky", "danger")
    pro_positive_signals = ("should", "opportunity", "benefit", "advantage", "succeed", "growth", "potential")

    def_negative_signals = ("will work", "great idea", "should proceed", "recommend", "endorse", "support this")
    def_positive_signals = ("risk", "concern", "weakness", "problem", "challenge", "fail", "danger", "caution")

    if expected_side == "prosecutor":
        neg_count = sum(1 for s in pro_negative_signals if s in opening)
        pos_count = sum(1 for s in pro_positive_signals if s in opening)
        if neg_count > pos_count:
            violations.append(
                f"Prosecutor opening contains more negative ({neg_count}) "
                f"than positive ({pos_count}) signals — possible directive violation"
            )
    elif expected_side == "defense":
        neg_count = sum(1 for s in def_negative_signals if s in opening)
        pos_count = sum(1 for s in def_positive_signals if s in opening)
        if neg_count > pos_count:
            violations.append(
                f"Defense opening contains more supportive ({neg_count}) "
                f"than critical ({pos_count}) signals — possible directive violation"
            )

    # Check claim count (constitutional directive requires exactly 4)
    claims = argument_data.get("claims", [])
    if len(claims) != 4:
        violations.append(f"Expected 4 claims, got {len(claims)}")

    # Check confidence sanity
    confidence = argument_data.get("confidence", 0)
    if confidence < 0.1 or confidence > 0.99:
        violations.append(f"Suspicious confidence value: {confidence}")

    compliant = len(violations) == 0
    if not compliant:
        logger.warning(
            "Constitutional compliance check for %s: %d violations — %s",
            expected_side, len(violations), "; ".join(violations),
        )

    return {
        "compliant": compliant,
        "violations": violations,
        "confidence": confidence,
        "claim_count": len(claims),
    }


def _adaptive_temperature(research_package: dict, base_temp: float = 0.7) -> float:
    """Compute adaptive LLM temperature based on research quality.

    When research grounding is strong (many web-sourced facts), we lower
    the temperature so agents produce more factual, evidence-anchored arguments.
    When research is sparse, we raise temperature slightly to encourage more
    creative reasoning and broader exploration of the argument space.

    This creates a feedback loop: better research → more grounded arguments →
    higher quality pipeline output.

    Args:
        research_package: The research output (may contain _quality_scores).
        base_temp: Default temperature when no quality data is available.

    Returns:
        Adjusted temperature between 0.4 and 0.85.
    """
    quality = research_package.get("_quality_scores", {})
    if not quality:
        return base_temp

    overall = quality.get("overall", 0.5)
    grounding = quality.get("grounding", 0.0)

    # Higher quality research → lower temp (more factual)
    # Lower quality research → higher temp (more creative exploration)
    temp_adjustment = (0.5 - overall) * 0.3  # ±0.15 range
    grounding_bonus = grounding * -0.1       # Up to -0.1 for fully grounded

    adjusted = base_temp + temp_adjustment + grounding_bonus
    clamped = max(0.4, min(0.85, adjusted))

    logger.info(
        "Adaptive temperature: %.2f (base=%.2f, quality=%.2f, grounding=%.2f)",
        clamped, base_temp, overall, grounding,
    )
    return round(clamped, 2)


async def prosecutor_node(state: VerdictState) -> dict:
    """Run the Prosecutor agent — argues FOR the decision.

    Constitutional directive: Must argue FOR regardless of personal assessment.
    Adversarial isolation: Receives only research_package (with authorship stripped),
    never defense output. Temperature is adaptively set based on research quality.
    """
    agent = ProsecutorAgent()
    decision = state["decision"]
    research = strip_authorship(state.get("research_package", {}))
    callback = _callback_registry.get(state.get("thread_id", ""))
    output_format = state.get("output_format", "executive")
    domain = state.get("domain", "business")
    tid = state.get("thread_id", "")

    # Adaptive temperature: adjust based on research quality
    agent.llm.temperature = _adaptive_temperature(state.get("research_package", {}))

    with pipeline_metrics.track("prosecutor"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.prosecutor.start", session_id=tid,
            ))
            argument = await agent.run(
                decision_question=decision["question"],
                research_package=research,
                output_format=output_format,
                domain=domain,
                stream_callback=callback,
            )
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.prosecutor.complete", session_id=tid,
                payload={"confidence": argument.confidence, "claim_count": len(argument.claims)},
            ))
            return {"prosecutor_argument": argument.model_dump(mode="json")}
        except Exception as e:
            logger.error("Prosecutor node failed: %s", e)
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.prosecutor.error", session_id=tid,
                payload={"error": str(e)}, priority=EventPriority.HIGH,
            ))
            return {"prosecutor_argument": None, "errors": [f"Prosecutor: {str(e)}"]}


async def defense_node(state: VerdictState) -> dict:
    """Run the Defense agent — argues AGAINST the decision.

    Constitutional directive: Must argue AGAINST regardless of personal assessment.
    Adversarial isolation: Receives only research_package (with authorship stripped),
    never prosecutor output. Domain-aware constitutional overlay applied.
    """
    agent = DefenseAgent()
    decision = state["decision"]
    research = strip_authorship(state.get("research_package", {}))
    callback = _callback_registry.get(state.get("thread_id", ""))
    output_format = state.get("output_format", "executive")
    domain = state.get("domain", "business")
    tid = state.get("thread_id", "")

    # Adaptive temperature: adjust based on research quality
    agent.llm.temperature = _adaptive_temperature(state.get("research_package", {}))

    with pipeline_metrics.track("defense"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.defense.start", session_id=tid,
            ))
            argument = await agent.run(
                decision_question=decision["question"],
                research_package=research,
                output_format=output_format,
                domain=domain,
                stream_callback=callback,
            )
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.defense.complete", session_id=tid,
                payload={"confidence": argument.confidence, "claim_count": len(argument.claims)},
            ))
            return {"defense_argument": argument.model_dump(mode="json")}
        except Exception as e:
            logger.error("Defense node failed: %s", e)
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.defense.error", session_id=tid,
                payload={"error": str(e)}, priority=EventPriority.HIGH,
            ))
            return {"defense_argument": None, "errors": [f"Defense: {str(e)}"]}


async def parallel_arguments_node(state: VerdictState) -> dict:
    """Run Prosecutor and Defense in true parallel.

    Both agents receive the same research package but are isolated from
    each other's reasoning — a core adversarial design constraint.
    """
    pro_task = asyncio.create_task(prosecutor_node(state))
    def_task = asyncio.create_task(defense_node(state))

    pro_result, def_result = await asyncio.gather(pro_task, def_task)

    merged = {}
    merged["prosecutor_argument"] = pro_result.get("prosecutor_argument")
    merged["defense_argument"] = def_result.get("defense_argument")

    # Argument quality scoring — evaluate both sides before cross-examination
    tid = state.get("thread_id", "")
    pro_quality = score_argument_quality(merged["prosecutor_argument"])
    def_quality = score_argument_quality(merged["defense_argument"])
    await pipeline_event_bus.publish(PipelineEvent(
        topic="pipeline.argument_quality", session_id=tid,
        payload={
            "prosecutor": {"grade": pro_quality["grade"], "overall": pro_quality["overall"]},
            "defense": {"grade": def_quality["grade"], "overall": def_quality["overall"]},
        },
    ))

    # Constitutional compliance validation — verify both sides argue as directed
    pro_compliance = _validate_constitutional_compliance(
        merged["prosecutor_argument"], "prosecutor"
    )
    def_compliance = _validate_constitutional_compliance(
        merged["defense_argument"], "defense"
    )

    if not pro_compliance["compliant"] or not def_compliance["compliant"]:
        await pipeline_event_bus.publish(PipelineEvent(
            topic="pipeline.constitutional_violation",
            session_id=tid,
            payload={
                "prosecutor": pro_compliance,
                "defense": def_compliance,
            },
            priority=EventPriority.HIGH,
        ))

    # Store quality scores in state — downstream nodes (cross-exam, witness,
    # synthesis) use these to prioritize claims and weight arguments.
    merged["argument_quality"] = {
        "prosecutor": {"grade": pro_quality["grade"], "overall": pro_quality["overall"]},
        "defense": {"grade": def_quality["grade"], "overall": def_quality["overall"]},
        "quality_gap": round(abs(pro_quality["overall"] - def_quality["overall"]), 3),
        "weaker_side": "defense" if pro_quality["overall"] > def_quality["overall"] else "prosecution",
    }

    errors = pro_result.get("errors", []) + def_result.get("errors", [])
    if errors:
        merged["errors"] = errors
    return merged


async def judge_cross_exam_node(state: VerdictState) -> dict:
    """Judge identifies contested claims and spawns witnesses."""
    from models.schemas import Argument

    judge = JudgeAgent()
    decision = state["decision"]
    callback = _callback_registry.get(state.get("thread_id", ""))

    pro_data = state.get("prosecutor_argument")
    def_data = state.get("defense_argument")

    if not pro_data or not def_data:
        return {"contested_claims": [], "errors": ["Missing arguments for cross-examination"]}

    pro_arg = Argument(**pro_data)
    def_arg = Argument(**def_data)
    tid = state.get("thread_id", "")

    # Build argument dependency graphs for structural analysis
    pro_claims = [{"id": c.id, "statement": c.statement, "evidence": c.evidence, "confidence": c.confidence}
                  for c in pro_arg.claims]
    def_claims = [{"id": c.id, "statement": c.statement, "evidence": c.evidence, "confidence": c.confidence}
                  for c in def_arg.claims]
    graph_analysis = build_argument_graphs(pro_claims, def_claims)

    # Enrich cross-examination with structural intelligence from argument graphs.
    # The judge can now prioritize claims with high cascading impact and target
    # foundation claims whose overruling would collapse entire argument branches.
    structural_guidance = ""
    comparative = graph_analysis.get("comparative", {})
    for side_key in ("prosecution", "defense"):
        side_data = graph_analysis.get(side_key, {})
        critical = side_data.get("critical_claims", [])
        foundation = side_data.get("foundation_claims", [])
        if critical:
            structural_guidance += f"\n{side_key.title()} critical claims (high cascading impact): {critical}"
        if foundation:
            structural_guidance += f"\n{side_key.title()} foundation claims (base assumptions): {foundation}"
    if comparative.get("coherence_differential"):
        structural_guidance += f"\nCoherence differential: {comparative['coherence_differential']:.3f}"

    with pipeline_metrics.track("judge_cross_exam"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.judge.cross_exam.start", session_id=tid,
                payload={"argument_graphs": comparative},
            ))
            contested = await judge.cross_examine(
                decision_question=decision["question"],
                prosecutor_argument=pro_arg,
                defense_argument=def_arg,
                stream_callback=callback,
                structural_analysis=structural_guidance if structural_guidance else None,
            )
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.judge.cross_exam.complete", session_id=tid,
                payload={"contested_count": len(contested)},
            ))
            return {"contested_claims": contested, "argument_graphs": graph_analysis}
        except Exception as e:
            logger.error("Judge cross-exam failed: %s", e)
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.judge.cross_exam.error", session_id=tid,
                payload={"error": str(e)}, priority=EventPriority.HIGH,
            ))
            return {"contested_claims": [], "errors": [f"Cross-exam: {str(e)}"]}


async def witness_node(state: VerdictState) -> dict:
    """Spawn witness agents in parallel to verify contested claims.

    Uses argument graph analysis (when available) to prioritize claims by
    cascading impact — verifying a high-impact claim first produces more
    valuable information for the verdict than verifying peripheral claims.
    """
    witness_agent = WitnessAgent()
    contested = state.get("contested_claims", [])
    callback = _callback_registry.get(state.get("thread_id", ""))

    tid = state.get("thread_id", "")

    if not contested:
        return {"witness_reports": []}

    # Build claim lookup from both arguments (adversarial isolation maintained)
    pro_claims = {}
    def_claims = {}
    pro_data = state.get("prosecutor_argument", {})
    def_data = state.get("defense_argument", {})

    if pro_data:
        for c in pro_data.get("claims", []):
            pro_claims[c["id"]] = c
    if def_data:
        for c in def_data.get("claims", []):
            def_claims[c["id"]] = c

    all_claims = {**pro_claims, **def_claims}

    async def verify_one(contested_claim: dict):
        claim_id = contested_claim.get("claim_id", "unknown")
        statement = contested_claim.get("statement", "")
        witness_type = contested_claim.get("witness_type", "fact")
        evidence = ""
        if claim_id in all_claims:
            evidence = all_claims[claim_id].get("evidence", "")

        return await witness_agent.verify_claim(
            claim_id=claim_id,
            claim_statement=statement,
            claim_evidence=evidence,
            witness_type=witness_type,
            stream_callback=callback,
        )

    # Prioritize contested claims using argument graph analysis when available.
    # Claims with higher cascading impact are verified first — overruling a
    # foundation claim has more verdict impact than overruling a peripheral one.
    graph_data = state.get("argument_graphs", {})
    if graph_data and len(contested) > 1:
        # Build claim_id → cascading_impact lookup from both sides
        impact_map: dict[str, int] = {}
        for side_key in ("prosecution", "defense"):
            per_claim = graph_data.get(side_key, {}).get("per_claim", {})
            for cid, metrics in per_claim.items():
                impact_map[cid] = metrics.get("cascading_impact", 0)

        # Sort contested by cascading impact (highest first), then original order
        contested = sorted(
            contested,
            key=lambda c: impact_map.get(c.get("claim_id", ""), 0),
            reverse=True,
        )
        logger.info(
            "Witness prioritization: reordered %d claims by cascading impact",
            len(contested),
        )

    with pipeline_metrics.track("witnesses"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.witnesses.start", session_id=tid,
                payload={"count": len(contested[:3])},
            ))
            tasks = [verify_one(cc) for cc in contested[:3]]  # Max 3 witnesses
            reports = await asyncio.gather(*tasks, return_exceptions=True)

            valid_reports = []
            for r in reports:
                if isinstance(r, Exception):
                    logger.error("Witness failed: %s", r)
                else:
                    valid_reports.append(r.model_dump(mode="json"))

            avg_confidence = (
                sum(r.get("confidence", 0.5) for r in valid_reports) / len(valid_reports)
                if valid_reports else 0.0
            )
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.witnesses.complete", session_id=tid,
                payload={
                    "verified": len(valid_reports),
                    "failed": len(reports) - len(valid_reports),
                    "avg_confidence": round(avg_confidence, 3),
                },
            ))
            return {"witness_reports": valid_reports}
        except Exception as e:
            logger.error("Witness node failed: %s", e)
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.witnesses.error", session_id=tid,
                payload={"error": str(e)}, priority=EventPriority.HIGH,
            ))
            return {"witness_reports": [], "errors": [f"Witnesses: {str(e)}"]}


def _calibrate_from_witnesses(
    pro_arg,
    def_arg,
    witness_reports: list,
    domain: str,
) -> None:
    """Use witness verdicts as ground truth to calibrate agent confidence.

    When a witness sustains a claim, the originating agent's confidence for
    that claim is recorded as "correct". When overruled, it's "incorrect".
    This builds per-agent, per-domain calibration curves over time — enabling
    detection of systematically overconfident or underconfident agents.
    """
    pro_claim_ids = {c.id: c.confidence for c in pro_arg.claims}
    def_claim_ids = {c.id: c.confidence for c in def_arg.claims}

    for w in witness_reports:
        claim_id = w.claim_id
        verdict = w.verdict_on_claim

        if verdict == "inconclusive":
            continue  # Skip — no ground truth

        was_correct = verdict == "sustained"

        if claim_id in pro_claim_ids:
            calibration_tracker.record(
                agent_name="prosecutor",
                domain=domain,
                confidence=pro_claim_ids[claim_id],
                was_correct=was_correct,
            )
        elif claim_id in def_claim_ids:
            calibration_tracker.record(
                agent_name="defense",
                domain=domain,
                confidence=def_claim_ids[claim_id],
                was_correct=was_correct,
            )

    # After recording enough data, fit Platt scaling so calibrate_confidence()
    # can correct raw scores in future pipeline runs. This is a lightweight
    # operation (200 gradient descent iterations on small data) and only
    # updates coefficients when sufficient data has accumulated.
    for agent_name in ("prosecutor", "defense"):
        cal = calibration_tracker.get_agent_calibration(agent_name)
        if cal and cal._total_predictions >= 10:
            cal.fit_platt_scaling()

    logger.info(
        "Calibration update — prosecutor ECE: %.4f, defense ECE: %.4f",
        (calibration_tracker.get_agent_calibration("prosecutor") or type("", (), {"expected_calibration_error": 0})).expected_calibration_error,
        (calibration_tracker.get_agent_calibration("defense") or type("", (), {"expected_calibration_error": 0})).expected_calibration_error,
    )


async def _run_verdict(state: VerdictState, use_low_temp: bool = False) -> dict:
    """Core verdict logic shared by all verdict node variants."""
    from models.schemas import Argument, WitnessReport

    judge = JudgeAgent()
    decision = state["decision"]
    callback = _callback_registry.get(state.get("thread_id", ""))
    tid = state.get("thread_id", "")

    pro_data = state.get("prosecutor_argument")
    def_data = state.get("defense_argument")
    witness_data = state.get("witness_reports", [])

    if not pro_data or not def_data:
        return {"verdict": None, "errors": ["Missing arguments for verdict"]}

    pro_arg = Argument(**pro_data)
    def_arg = Argument(**def_data)
    reports = [WitnessReport(**w) for w in witness_data]

    if use_low_temp:
        logger.info("Hallucination guard active: overriding judge temperature to 0.3")
        judge.llm.temperature = 0.3

    # Calibrate agent confidence against witness ground truth
    _calibrate_from_witnesses(pro_arg, def_arg, reports, state.get("domain", "business"))

    # Apply Platt-calibrated confidence correction when available.
    # If enough historical data has been recorded, calibrate_confidence()
    # maps raw agent confidence through a learned sigmoid to correct
    # systematic over/underconfidence.
    pro_cal = calibration_tracker.get_agent_calibration("prosecutor")
    def_cal = calibration_tracker.get_agent_calibration("defense")
    if pro_cal and hasattr(pro_cal, "_platt_a"):
        calibrated_pro = pro_cal.calibrate_confidence(pro_arg.confidence)
        logger.info("Platt-calibrated prosecutor confidence: %.3f → %.3f", pro_arg.confidence, calibrated_pro)
    if def_cal and hasattr(def_cal, "_platt_a"):
        calibrated_def = def_cal.calibrate_confidence(def_arg.confidence)
        logger.info("Platt-calibrated defense confidence: %.3f → %.3f", def_arg.confidence, calibrated_def)

    verdict_path = "low_temp" if use_low_temp else "normal"
    with pipeline_metrics.track("verdict"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.judge.verdict.start", session_id=tid,
                payload={"path": verdict_path, "witness_count": len(reports)},
            ))
            verdict = await judge.deliver_verdict(
                decision_question=decision["question"],
                prosecutor_argument=pro_arg,
                defense_argument=def_arg,
                witness_reports=reports,
                decision_id=decision["id"],
                stream_callback=callback,
            )
            # Run verdict stability analysis — perturbation testing
            evidence_scores = judge.compute_evidence_score(pro_arg, def_arg, reports)
            stability = full_stability_analysis(
                prosecution_score=evidence_scores["prosecution_score"],
                defense_score=evidence_scores["defense_score"],
                ruling=verdict.ruling,
                witness_reports=[w.model_dump(mode="json") for w in reports],
                prosecution_base_confidence=pro_arg.confidence,
                defense_base_confidence=def_arg.confidence,
            )

            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.judge.verdict.complete", session_id=tid,
                payload={
                    "ruling": verdict.ruling,
                    "confidence": verdict.confidence,
                    "path": verdict_path,
                    "stability": stability["combined_robustness"],
                    "verdict_is_robust": stability["verdict_is_robust"],
                },
            ))
            # Store stability in state — synthesis uses this to gauge how
            # cautious its recommendations should be.
            return {
                "verdict": verdict.model_dump(mode="json"),
                "verdict_stability": {
                    "combined_robustness": stability["combined_robustness"],
                    "verdict_is_robust": stability["verdict_is_robust"],
                    "evidence_margin": stability.get("evidence_margin", {}).get("classification", "unknown"),
                    "flip_rate": stability.get("perturbation_stability", {}).get("flip_count", 0),
                },
            }
        except Exception as e:
            logger.error("Judge verdict failed: %s", e)
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.judge.verdict.error", session_id=tid,
                payload={"error": str(e)}, priority=EventPriority.HIGH,
            ))
            return {"verdict": None, "errors": [f"Verdict: {str(e)}"]}


async def judge_verdict_node(state: VerdictState) -> dict:
    """Judge delivers the final verdict (normal confidence path)."""
    return await _run_verdict(state, use_low_temp=False)


async def judge_verdict_with_review_node(state: VerdictState) -> dict:
    """Judge delivers verdict after low-confidence interrupt_before checkpoint.

    This node is reached when avg witness confidence < 0.6. When the graph is
    compiled with interrupt_before=['verdict_with_review'], execution pauses
    here to allow human review of witness reports before the ruling is issued.
    """
    logger.info("Verdict node (low confidence path): interrupt_before checkpoint reached")
    callback = _callback_registry.get(state.get("thread_id", ""))
    if callback:
        await callback(StreamEvent(
            event_type="verdict_start",
            agent="judge",
            content="Low witness confidence detected — proceeding with caution.\n",
        ))
    return await _run_verdict(state, use_low_temp=False)


async def judge_verdict_low_temp_node(state: VerdictState) -> dict:
    """Judge delivers verdict with temperature=0.3 hallucination guard.

    Triggered when confidence >= 0.9 AND a witness overruled a claim,
    which is a hallucination risk signal. Using temperature=0.3 produces
    more deterministic, grounded output.
    """
    logger.info("Verdict node (hallucination guard): using temperature=0.3")
    callback = _callback_registry.get(state.get("thread_id", ""))
    if callback:
        await callback(StreamEvent(
            event_type="verdict_start",
            agent="judge",
            content="Hallucination guard engaged — using conservative temperature.\n",
        ))
    return await _run_verdict(state, use_low_temp=True)


async def synthesis_node(state: VerdictState) -> dict:
    """Synthesis agent produces the battle-tested improved version.

    Uses domain-aware few-shot synthesis anchors from YAML config to ground
    recommended_actions in domain-specific, time-bound action plans.
    """
    from models.schemas import Argument, WitnessReport, VerdictResult

    agent = SynthesisAgent()
    decision = state["decision"]
    callback = _callback_registry.get(state.get("thread_id", ""))
    output_format = state.get("output_format", "executive")
    domain = state.get("domain", "business")

    pro_data = state.get("prosecutor_argument")
    def_data = state.get("defense_argument")
    verdict_data = state.get("verdict")

    if not pro_data or not def_data or not verdict_data:
        return {"synthesis": None, "errors": ["Missing data for synthesis"]}

    pro_arg = Argument(**pro_data)
    def_arg = Argument(**def_data)
    reports = [WitnessReport(**w) for w in state.get("witness_reports", [])]
    verdict = VerdictResult(**verdict_data)

    tid = state.get("thread_id", "")

    # Pass verdict stability and argument quality to synthesis so it can
    # calibrate recommendation confidence and flag fragile verdicts.
    stability_data = state.get("verdict_stability")
    quality_data = state.get("argument_quality")

    with pipeline_metrics.track("synthesis"):
        try:
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.synthesis.start", session_id=tid,
            ))
            synthesis = await agent.run(
                decision_question=decision["question"],
                research_package=state.get("research_package", {}),
                prosecutor_argument=pro_arg,
                defense_argument=def_arg,
                witness_reports=reports,
                verdict=verdict,
                output_format=output_format,
                domain=domain,
                stream_callback=callback,
                verdict_stability=stability_data,
                argument_quality=quality_data,
            )
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.synthesis.complete", session_id=tid,
                payload={
                    "strength_score": synthesis.strength_score,
                    "actions_count": len(synthesis.recommended_actions),
                    "objections_addressed": len(synthesis.addressed_objections),
                },
            ))
            return {"synthesis": synthesis.model_dump(mode="json")}
        except Exception as e:
            logger.error("Synthesis node failed: %s", e)
            await pipeline_event_bus.publish(PipelineEvent(
                topic="agent.synthesis.error", session_id=tid,
                payload={"error": str(e)}, priority=EventPriority.HIGH,
            ))
            return {"synthesis": None, "errors": [f"Synthesis: {str(e)}"]}


# ── Build the graph ─────────────────────────────────────────────────────────


def _should_spawn_witnesses(state: VerdictState) -> str:
    """Conditional edge: decide whether to spawn witnesses for verification.

    Uses two signals for the spawning decision:
    1. Contested claims from cross-examination (primary gate)
    2. Argument quality gap — if one side is significantly weaker (quality
       gap > 0.2), witnesses are spawned even with few contested claims to
       ensure the weaker argument is stress-tested.

    This prevents low-quality arguments from sailing through un-verified
    when the cross-examination happens to find few keyword overlaps.
    """
    contested = state.get("contested_claims", [])

    # Primary gate: cross-examination identified contested claims
    if contested and len(contested) > 0:
        logger.info(
            "Conditional edge: spawning %d witnesses for contested claims",
            len(contested),
        )
        return "witnesses"

    # Secondary gate: large quality gap between sides suggests one argument
    # may be weak enough to need verification even without direct conflict.
    quality_data = state.get("argument_quality")
    if quality_data and quality_data.get("quality_gap", 0) > 0.2:
        logger.info(
            "Conditional edge: quality gap %.3f (weaker: %s) — "
            "spawning witnesses despite no contested claims to stress-test weaker side",
            quality_data["quality_gap"],
            quality_data.get("weaker_side", "unknown"),
        )
        return "witnesses"

    logger.info("Conditional edge: no contested claims, skipping witnesses")
    return "verdict"


LOW_CONFIDENCE_THRESHOLD = 0.6
HIGH_CONFIDENCE_OVERRULE_THRESHOLD = 0.9

# Domain-specific confidence thresholds — domains with higher stakes
# require higher witness agreement before proceeding without review.
DOMAIN_CONFIDENCE_THRESHOLDS: dict[str, float] = {
    "medical": 0.7,    # Medical decisions require higher confidence
    "legal": 0.65,     # Legal decisions have moderate risk threshold
    "financial": 0.65, # Financial decisions need careful verification
    "business": 0.6,   # Default business threshold
    "technology": 0.55, # Technical decisions can tolerate more uncertainty
    "hiring": 0.6,     # Hiring decisions at default threshold
}


def _confidence_gate(state: VerdictState) -> str:
    """Multi-factor conditional edge: evaluate witness evidence before routing.

    Uses four factors for verdict routing:
    1. Average witness confidence (domain-adjusted threshold)
    2. Witness agreement ratio (what fraction agree on verdict direction)
    3. Overrule detection (high confidence + overruled = hallucination risk)
    4. Confidence variance (high disagreement among witnesses → review)

    Routing outcomes:
    - verdict_with_review: low confidence OR high variance OR low agreement
    - verdict_low_temp: high confidence + overruled (hallucination guard)
    - verdict: normal path (sufficient agreement and confidence)
    """
    witness_data = state.get("witness_reports", [])
    if not witness_data:
        return "verdict"

    domain = state.get("domain", "business")
    low_threshold = DOMAIN_CONFIDENCE_THRESHOLDS.get(domain, LOW_CONFIDENCE_THRESHOLD)

    confidences = []
    verdicts_on_claims = []
    has_overruled = False
    for w in witness_data:
        if isinstance(w, dict):
            conf = w.get("confidence", 0.5)
            verdict_val = w.get("verdict_on_claim", "inconclusive")
            if verdict_val == "overruled":
                has_overruled = True
            verdicts_on_claims.append(verdict_val)
        else:
            conf = 0.5
            verdicts_on_claims.append("inconclusive")
        confidences.append(conf)

    n = len(confidences)
    avg_confidence = sum(confidences) / n

    # Factor 2: Witness agreement ratio — what fraction of witnesses agree?
    # High disagreement (e.g., one sustained, one overruled) suggests the
    # evidence is genuinely contested and warrants careful review.
    verdict_counts: dict[str, int] = {}
    for v in verdicts_on_claims:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    majority_count = max(verdict_counts.values()) if verdict_counts else 0
    agreement_ratio = majority_count / n if n > 0 else 1.0

    # Factor 3: Confidence variance — high spread means witnesses disagree
    # on how certain they are, even if average looks acceptable.
    mean_conf = avg_confidence
    variance = sum((c - mean_conf) ** 2 for c in confidences) / n if n > 1 else 0.0

    logger.info(
        "Confidence gate [%s]: avg=%.2f (threshold=%.2f), agreement=%.0f%%, "
        "variance=%.3f, witnesses=%d, has_overruled=%s",
        domain, avg_confidence, low_threshold, agreement_ratio * 100,
        variance, n, has_overruled,
    )

    # Route to review if confidence is low OR witnesses strongly disagree
    if avg_confidence < low_threshold:
        logger.warning(
            "Low witness confidence (%.2f < %.2f for %s domain) — "
            "routing to verdict_with_review",
            avg_confidence, low_threshold, domain,
        )
        return "verdict_with_review"

    if agreement_ratio < 0.5 and n >= 2:
        logger.warning(
            "Low witness agreement (%.0f%%) — witnesses disagree on claim "
            "verdicts, routing to verdict_with_review for cautious ruling",
            agreement_ratio * 100,
        )
        return "verdict_with_review"

    if variance > 0.06 and n >= 2:
        logger.warning(
            "High confidence variance (%.3f) — witness certainty levels diverge "
            "significantly, routing to verdict_with_review",
            variance,
        )
        return "verdict_with_review"

    # Hallucination guard: confident witnesses overruling claims is suspicious
    if avg_confidence >= HIGH_CONFIDENCE_OVERRULE_THRESHOLD and has_overruled:
        logger.warning(
            "High confidence (%.2f) with overruled claims — hallucination guard: "
            "verdict node will retry with temperature=0.3",
            avg_confidence,
        )
        return "verdict_low_temp"

    return "verdict"


def _get_checkpointer():
    """Create the appropriate checkpointer based on environment.

    Uses AsyncRedisSaver when REDIS_URL is set for production fault tolerance.
    Falls back to MemorySaver for local development.
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url and _REDIS_AVAILABLE:
        logger.info("Using AsyncRedisSaver for checkpointing (Redis URL configured)")
        return AsyncRedisSaver.from_conn_string(redis_url)
    if redis_url and not _REDIS_AVAILABLE:
        logger.warning(
            "REDIS_URL is set but langgraph[redis] not installed — "
            "falling back to MemorySaver"
        )
    return MemorySaver()


def build_verdict_graph(interrupt_before_verdict: bool = False) -> StateGraph:
    """Construct and compile the Verdict LangGraph.

    Args:
        interrupt_before_verdict: If True, graph pauses before judge_verdict
            to allow human review of witness reports (human-in-the-loop mode).

    The graph uses conditional edges for dynamic witness spawning:
      cross_examination → _should_spawn_witnesses → witnesses | verdict
      witnesses → _confidence_gate → verdict

    Checkpointer is selected at runtime: AsyncRedisSaver if REDIS_URL is set,
    MemorySaver otherwise.
    """
    graph = StateGraph(VerdictState)

    graph.add_node("research", research_node)
    graph.add_node("arguments", parallel_arguments_node)
    graph.add_node("cross_examination", judge_cross_exam_node)
    graph.add_node("witnesses", witness_node)
    graph.add_node("verdict", judge_verdict_node)
    graph.add_node("verdict_with_review", judge_verdict_with_review_node)
    graph.add_node("verdict_low_temp", judge_verdict_low_temp_node)
    graph.add_node("synthesis", synthesis_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "arguments")
    graph.add_edge("arguments", "cross_examination")

    # Dynamic witness spawning via conditional edge — Judge determines
    # which claims are contested, then witnesses are spawned per claim type.
    # If no claims are contested, skip witnesses entirely.
    graph.add_conditional_edges(
        "cross_examination",
        _should_spawn_witnesses,
        {"witnesses": "witnesses", "verdict": "verdict"},
    )

    # Confidence-based routing after witnesses complete:
    # - Normal confidence → verdict (standard path)
    # - Low confidence (<0.6) → verdict_with_review (interrupt_before checkpoint)
    # - High confidence (>0.9) + overruled → verdict_low_temp (hallucination guard)
    graph.add_conditional_edges(
        "witnesses",
        _confidence_gate,
        {
            "verdict": "verdict",
            "verdict_with_review": "verdict_with_review",
            "verdict_low_temp": "verdict_low_temp",
        },
    )

    # All verdict variants converge to synthesis
    graph.add_edge("verdict", "synthesis")
    graph.add_edge("verdict_with_review", "synthesis")
    graph.add_edge("verdict_low_temp", "synthesis")
    graph.add_edge("synthesis", END)

    checkpointer = _get_checkpointer()

    # interrupt_before pauses graph execution before the low-confidence
    # verdict node, enabling human-in-the-loop review of witness reports
    interrupt_nodes = ["verdict_with_review"] if interrupt_before_verdict else []

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_nodes,
    )


async def run_verdict_graph(
    decision: dict,
    stream_callback: Optional[Callable] = None,
    output_format: str = "executive",
    domain: str = "business",
    thread_id: Optional[str] = None,
) -> VerdictState:
    """Execute the full verdict pipeline.

    Args:
        decision: Dict with 'id', 'question', and optional 'context'.
        stream_callback: Async callable that receives StreamEvent objects.
        output_format: One of 'executive', 'technical', 'legal', 'investor'.
        domain: Auto-detected domain (business, legal, medical, financial, etc.).
        thread_id: Optional thread ID for checkpointing / resume support.

    Returns:
        The final VerdictState with all results.
    """
    interrupt_before = bool(os.getenv("INTERRUPT_BEFORE_VERDICT"))
    compiled = build_verdict_graph(interrupt_before_verdict=interrupt_before)

    tid = thread_id or decision.get("id", "default")

    # Register the callback outside the state so the checkpointer
    # never tries to serialize a function object.
    if stream_callback:
        _callback_registry[tid] = stream_callback

    initial_state: VerdictState = {
        "decision": decision,
        "output_format": output_format,
        "domain": domain,
        "research_package": None,
        "prosecutor_argument": None,
        "defense_argument": None,
        "argument_quality": None,
        "argument_graphs": None,
        "contested_claims": None,
        "witness_reports": None,
        "cross_examination": None,
        "verdict": None,
        "verdict_stability": None,
        "synthesis": None,
        "thread_id": tid,
        "errors": [],
    }

    config = {"configurable": {"thread_id": tid}}

    logger.info("Starting verdict graph for decision: %s", decision.get("question", "")[:80])

    # Emit pipeline start event for observability
    await pipeline_event_bus.publish(PipelineEvent(
        topic="pipeline.start",
        payload={"decision_id": decision.get("id", ""), "domain": domain, "format": output_format},
        session_id=tid,
        priority=EventPriority.HIGH,
    ))

    try:
        result = await compiled.ainvoke(initial_state, config=config)
        logger.info("Verdict graph complete. Errors: %s", result.get("errors", []))

        # Emit pipeline complete event
        await pipeline_event_bus.publish(PipelineEvent(
            topic="pipeline.complete",
            payload={
                "decision_id": decision.get("id", ""),
                "ruling": result.get("verdict", {}).get("ruling") if result.get("verdict") else None,
                "error_count": len(result.get("errors", [])),
            },
            session_id=tid,
            priority=EventPriority.HIGH,
        ))

        return result
    except Exception as e:
        await pipeline_event_bus.publish(PipelineEvent(
            topic="pipeline.error",
            payload={"error": str(e)},
            session_id=tid,
            priority=EventPriority.CRITICAL,
        ))
        raise
    finally:
        _callback_registry.pop(tid, None)
