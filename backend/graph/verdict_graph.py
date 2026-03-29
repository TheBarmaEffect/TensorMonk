"""LangGraph StateGraph for the Verdict adversarial courtroom pipeline.

Graph topology:
  input → research → [prosecutor, defense] (parallel) → judge_cross_exam
  → witness_nodes (parallel) → judge_verdict → synthesis → END

Checkpointing: Uses MemorySaver by default for in-process thread persistence.
For production deployments, swap MemorySaver for a Redis-backed checkpointer:
  from langgraph.checkpoint.redis import RedisSaver
  checkpointer = RedisSaver.from_conn_string(settings.redis_url)

interrupt_before: The graph supports pausing before the 'verdict' node to allow
human review of witness reports before the final ruling is issued.
"""

import asyncio
import logging
from typing import TypedDict, Optional, Annotated, Callable
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.research import ResearchAgent
from agents.prosecutor import ProsecutorAgent
from agents.defense import DefenseAgent
from agents.judge import JudgeAgent
from agents.witness import WitnessAgent
from agents.synthesis import SynthesisAgent
from models.schemas import StreamEvent

logger = logging.getLogger(__name__)


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
    stream_callback: Optional[Callable]
    errors: Annotated[list, operator.add]


# ── Node functions ──────────────────────────────────────────────────────────


async def research_node(state: VerdictState) -> dict:
    """Run the Research agent to produce a neutral research package.

    The research package is the ONLY shared context between prosecutor and
    defense — authorship is anonymous (neither agent knows who wrote it).
    """
    agent = ResearchAgent()
    decision = state["decision"]
    callback = state.get("stream_callback")
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
    Adversarial isolation: Receives only research_package, not defense output.
    """
    agent = ProsecutorAgent()
    decision = state["decision"]
    research = state.get("research_package", {})
    callback = state.get("stream_callback")
    output_format = state.get("output_format", "executive")

    try:
        argument = await agent.run(
            decision_question=decision["question"],
            research_package=research,
            output_format=output_format,
            stream_callback=callback,
        )
        return {"prosecutor_argument": argument.model_dump(mode="json")}
    except Exception as e:
        logger.error("Prosecutor node failed: %s", e)
        return {"prosecutor_argument": None, "errors": [f"Prosecutor: {str(e)}"]}


async def defense_node(state: VerdictState) -> dict:
    """Run the Defense agent — argues AGAINST the decision.

    Constitutional directive: Must argue AGAINST regardless of personal assessment.
    Adversarial isolation: Receives only research_package, not prosecutor output.
    """
    agent = DefenseAgent()
    decision = state["decision"]
    research = state.get("research_package", {})
    callback = state.get("stream_callback")
    output_format = state.get("output_format", "executive")

    try:
        argument = await agent.run(
            decision_question=decision["question"],
            research_package=research,
            output_format=output_format,
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
    callback = state.get("stream_callback")

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
    callback = state.get("stream_callback")

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


async def judge_verdict_node(state: VerdictState) -> dict:
    """Judge delivers the final verdict.

    This node is the interrupt_before checkpoint — the graph can pause here
    to allow human review of witness reports before ruling is issued.
    """
    from models.schemas import Argument, WitnessReport

    judge = JudgeAgent()
    decision = state["decision"]
    callback = state.get("stream_callback")

    pro_data = state.get("prosecutor_argument")
    def_data = state.get("defense_argument")
    witness_data = state.get("witness_reports", [])

    if not pro_data or not def_data:
        return {"verdict": None, "errors": ["Missing arguments for verdict"]}

    pro_arg = Argument(**pro_data)
    def_arg = Argument(**def_data)
    reports = [WitnessReport(**w) for w in witness_data]

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


async def synthesis_node(state: VerdictState) -> dict:
    """Synthesis agent produces the battle-tested improved version."""
    from models.schemas import Argument, WitnessReport, VerdictResult

    agent = SynthesisAgent()
    decision = state["decision"]
    callback = state.get("stream_callback")
    output_format = state.get("output_format", "executive")

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
            stream_callback=callback,
        )
        return {"synthesis": synthesis.model_dump(mode="json")}
    except Exception as e:
        logger.error("Synthesis node failed: %s", e)
        return {"synthesis": None, "errors": [f"Synthesis: {str(e)}"]}


# ── Build the graph ─────────────────────────────────────────────────────────


def build_verdict_graph(interrupt_before_verdict: bool = False) -> StateGraph:
    """Construct and compile the Verdict LangGraph.

    Args:
        interrupt_before_verdict: If True, graph pauses before judge_verdict
            to allow human review of witness reports (human-in-the-loop mode).
    """
    graph = StateGraph(VerdictState)

    graph.add_node("research", research_node)
    graph.add_node("arguments", parallel_arguments_node)
    graph.add_node("cross_examination", judge_cross_exam_node)
    graph.add_node("witnesses", witness_node)
    graph.add_node("verdict", judge_verdict_node)
    graph.add_node("synthesis", synthesis_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "arguments")
    graph.add_edge("arguments", "cross_examination")
    graph.add_edge("cross_examination", "witnesses")
    graph.add_edge("witnesses", "verdict")
    graph.add_edge("verdict", "synthesis")
    graph.add_edge("synthesis", END)

    # MemorySaver provides thread-level checkpointing so graph state is
    # persisted between steps and resumable. For production, swap with:
    #   from langgraph.checkpoint.redis import RedisSaver
    #   checkpointer = RedisSaver.from_conn_string(os.getenv("REDIS_URL"))
    checkpointer = MemorySaver()

    interrupt_nodes = ["verdict"] if interrupt_before_verdict else []

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
        "stream_callback": stream_callback,
        "errors": [],
    }

    config = {"configurable": {"thread_id": thread_id or decision.get("id", "default")}}

    logger.info("Starting verdict graph for decision: %s", decision.get("question", "")[:80])

    result = await compiled.ainvoke(initial_state, config=config)

    logger.info("Verdict graph complete. Errors: %s", result.get("errors", []))
    return result
