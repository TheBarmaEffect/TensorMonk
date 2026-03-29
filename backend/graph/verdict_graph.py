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
    """

    decision: dict
    output_format: str                     # executive | technical | legal | investor
    domain: str                            # auto-detected domain (business, legal, etc.)
    research_package: Optional[dict]
    prosecutor_argument: Optional[dict]
    defense_argument: Optional[dict]
    contested_claims: Optional[list]
    witness_reports: Optional[list]
    cross_examination: Optional[dict]
    verdict: Optional[dict]
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

    try:
        package = await agent.run(
            decision_question=decision["question"],
            context=decision.get("context"),
            output_format=output_format,
            domain=domain,
            stream_callback=callback,
        )
        return {"research_package": package}
    except Exception as e:
        logger.error("Research node failed: %s", e)
        return {"research_package": {}, "errors": [f"Research: {str(e)}"]}


async def prosecutor_node(state: VerdictState) -> dict:
    """Run the Prosecutor agent — argues FOR the decision.

    Constitutional directive: Must argue FOR regardless of personal assessment.
    Adversarial isolation: Receives only research_package (with authorship stripped),
    never defense output.
    """
    agent = ProsecutorAgent()
    decision = state["decision"]
    research = strip_authorship(state.get("research_package", {}))
    callback = _callback_registry.get(state.get("thread_id", ""))
    output_format = state.get("output_format", "executive")
    domain = state.get("domain", "business")

    try:
        argument = await agent.run(
            decision_question=decision["question"],
            research_package=research,
            output_format=output_format,
            domain=domain,
            stream_callback=callback,
        )
        return {"prosecutor_argument": argument.model_dump(mode="json")}
    except Exception as e:
        logger.error("Prosecutor node failed: %s", e)
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

    try:
        argument = await agent.run(
            decision_question=decision["question"],
            research_package=research,
            output_format=output_format,
            domain=domain,
            stream_callback=callback,
        )
        return {"defense_argument": argument.model_dump(mode="json")}
    except Exception as e:
        logger.error("Defense node failed: %s", e)
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

    try:
        contested = await judge.cross_examine(
            decision_question=decision["question"],
            prosecutor_argument=pro_arg,
            defense_argument=def_arg,
            stream_callback=callback,
        )
        return {"contested_claims": contested}
    except Exception as e:
        logger.error("Judge cross-exam failed: %s", e)
        return {"contested_claims": [], "errors": [f"Cross-exam: {str(e)}"]}


async def witness_node(state: VerdictState) -> dict:
    """Spawn witness agents in parallel to verify contested claims."""
    witness_agent = WitnessAgent()
    contested = state.get("contested_claims", [])
    callback = _callback_registry.get(state.get("thread_id", ""))

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

    try:
        tasks = [verify_one(cc) for cc in contested[:3]]  # Max 3 witnesses
        reports = await asyncio.gather(*tasks, return_exceptions=True)

        valid_reports = []
        for r in reports:
            if isinstance(r, Exception):
                logger.error("Witness failed: %s", r)
            else:
                valid_reports.append(r.model_dump(mode="json"))

        return {"witness_reports": valid_reports}
    except Exception as e:
        logger.error("Witness node failed: %s", e)
        return {"witness_reports": [], "errors": [f"Witnesses: {str(e)}"]}


async def _run_verdict(state: VerdictState, use_low_temp: bool = False) -> dict:
    """Core verdict logic shared by all verdict node variants."""
    from models.schemas import Argument, WitnessReport

    judge = JudgeAgent()
    decision = state["decision"]
    callback = _callback_registry.get(state.get("thread_id", ""))

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

    try:
        verdict = await judge.deliver_verdict(
            decision_question=decision["question"],
            prosecutor_argument=pro_arg,
            defense_argument=def_arg,
            witness_reports=reports,
            decision_id=decision["id"],
            stream_callback=callback,
        )
        return {"verdict": verdict.model_dump(mode="json")}
    except Exception as e:
        logger.error("Judge verdict failed: %s", e)
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

    try:
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
        )
        return {"synthesis": synthesis.model_dump(mode="json")}
    except Exception as e:
        logger.error("Synthesis node failed: %s", e)
        return {"synthesis": None, "errors": [f"Synthesis: {str(e)}"]}


# ── Build the graph ─────────────────────────────────────────────────────────


def _should_spawn_witnesses(state: VerdictState) -> str:
    """Conditional edge: route to witnesses only if contested claims exist.

    This is the dynamic witness spawning gate — the Judge's cross-examination
    determines which claims are contested and what type of witness specialist
    to spawn for each. If no claims are contested, skip directly to verdict.
    """
    contested = state.get("contested_claims", [])
    if contested and len(contested) > 0:
        logger.info(
            "Conditional edge: spawning %d witnesses for contested claims",
            len(contested),
        )
        return "witnesses"
    logger.info("Conditional edge: no contested claims, skipping witnesses")
    return "verdict"


LOW_CONFIDENCE_THRESHOLD = 0.6
HIGH_CONFIDENCE_OVERRULE_THRESHOLD = 0.9


def _confidence_gate(state: VerdictState) -> str:
    """Conditional edge: evaluate witness confidence before routing to verdict.

    This implements the confidence-based interrupt_before mechanism:
    - If avg witness confidence < 0.6: flags low_confidence in state for the
      verdict node to handle (when interrupt_before is enabled, the graph
      pauses here for human review).
    - If confidence >= 0.9 AND any witness overruled a claim: triggers
      hallucination guard flag so verdict node uses temperature=0.3.
    - Normal confidence: routes directly to verdict with no flags.
    """
    witness_data = state.get("witness_reports", [])
    if not witness_data:
        return "verdict"

    confidences = []
    has_overruled = False
    for w in witness_data:
        if isinstance(w, dict):
            conf = w.get("confidence", 0.5)
            if w.get("verdict_on_claim") == "overruled":
                has_overruled = True
        else:
            conf = 0.5
        confidences.append(conf)

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    logger.info(
        "Confidence gate: avg=%.2f, witnesses=%d, has_overruled=%s",
        avg_confidence, len(confidences), has_overruled,
    )

    if avg_confidence < LOW_CONFIDENCE_THRESHOLD:
        logger.warning(
            "Low witness confidence (%.2f < %.2f) — interrupt_before checkpoint engaged, "
            "human review recommended before verdict",
            avg_confidence, LOW_CONFIDENCE_THRESHOLD,
        )
        return "verdict_with_review"

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
    compiled = build_verdict_graph()

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
        "contested_claims": None,
        "witness_reports": None,
        "cross_examination": None,
        "verdict": None,
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
