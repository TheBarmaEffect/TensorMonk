"""Pydantic v2 data models for the Verdict courtroom system.

All agent outputs are validated against these schemas before being accepted
into the LangGraph state. Malformed output triggers the hallucination guard
retry mechanism (temperature=0.3 deterministic recovery).

Models follow a strict data flow:
    Decision → ResearchPackage (dict) → Argument (Prosecutor/Defense)
    → CrossExamination → WitnessReport → VerdictResult → Synthesis
    → StreamEvent (streamed to frontend via WebSocket)

Confidence scores are bounded [0.0, 1.0] via Pydantic Field constraints.
Witness verdicts are normalized from free-form LLM text to the enum
{sustained, overruled, inconclusive} via a field_validator.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
import uuid


class Decision(BaseModel):
    """A decision submitted for adversarial evaluation.

    Auto-generates a UUID on creation and timestamps the submission.
    This is the root entity that all downstream agents reference.

    Attributes:
        id: Unique identifier (auto-generated UUID4)
        question: The decision or idea to evaluate (10-2000 chars)
        context: Optional additional context for the decision
        created_at: UTC timestamp of submission
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    context: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Claim(BaseModel):
    """A single claim made by a Prosecutor or Defense agent.

    Each claim has a statement, supporting evidence, and a confidence
    score indicating how strongly the agent believes in this claim.
    The verified field is set later by Witness agents.

    Attributes:
        id: Unique claim identifier for cross-referencing with witnesses
        statement: The factual assertion being made
        evidence: Supporting data or reasoning for the claim
        confidence: Agent's confidence in this claim [0.0-1.0]
        verified: Set by witnesses — True if sustained, False if overruled
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    verified: Optional[bool] = None


class Argument(BaseModel):
    """A structured argument from either Prosecutor or Defense.

    Contains an opening statement, a list of claims with evidence,
    and an overall confidence score. The agent field is enforced
    as a literal to prevent miscategorization.

    Attributes:
        agent: Which adversarial agent produced this ('prosecutor' | 'defense')
        opening: Opening statement summarizing the argument
        claims: List of specific claims with evidence and confidence
        confidence: Overall argument strength [0.0-1.0]
        timestamp: When the argument was generated
    """

    agent: Literal["prosecutor", "defense"]
    opening: str
    claims: list[Claim]
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WitnessReport(BaseModel):
    """A verification report from a specialist Witness agent.

    Witnesses are dynamically spawned by the Judge to verify contested
    claims. Each report contains a verdict (sustained/overruled/inconclusive),
    a resolution explaining the finding, and a confidence score.

    The verdict_on_claim field uses a field_validator to normalize
    free-form LLM text (e.g., "SUSTAINED", "partially true", "Confirmed")
    into the valid enum values.

    Attributes:
        claim_id: ID of the claim being verified
        witness_type: Specialist type ('fact' | 'data' | 'precedent')
        resolution: Detailed explanation of the verification finding
        confidence: Witness's confidence in their verdict [0.0-1.0]
        verdict_on_claim: Normalized verdict ('sustained' | 'overruled' | 'inconclusive')
    """

    claim_id: str
    witness_type: Literal["fact", "data", "precedent"]
    resolution: str
    confidence: float = Field(ge=0.0, le=1.0)
    verdict_on_claim: Literal["sustained", "overruled", "inconclusive"]

    @field_validator('verdict_on_claim', mode='before')
    @classmethod
    def normalize_verdict(cls, v: str) -> str:
        """Normalize LLM's free-form verdicts to valid enum values.

        Maps various affirmative words to 'sustained', negative words
        to 'overruled', and everything else to 'inconclusive'.
        """
        if not isinstance(v, str):
            return 'inconclusive'
        v_lower = v.lower().strip()
        if any(word in v_lower for word in ('sustain', 'accurate', 'true', 'confirm', 'support', 'valid', 'verified')):
            return 'sustained'
        if any(word in v_lower for word in ('overrule', 'false', 'reject', 'invalid', 'refute', 'denied', 'incorrect')):
            return 'overruled'
        if v_lower in ('sustained', 'overruled', 'inconclusive'):
            return v_lower
        return 'inconclusive'


class CrossExamination(BaseModel):
    """Cross-examination results from the Judge.

    Contains the list of contested claims identified during examination,
    all witness reports, and the judge's preliminary notes.

    Attributes:
        contested_claims: Claim IDs that both sides dispute
        witness_reports: Verification reports from spawned witnesses
        judge_notes: Judge's observations on argument quality
    """

    contested_claims: list[str]
    witness_reports: list[WitnessReport]
    judge_notes: str


class VerdictResult(BaseModel):
    """The Judge's final ruling on the decision.

    Contains the verdict (proceed/reject/conditional), detailed reasoning,
    key factors that influenced the ruling, and a confidence score.

    Attributes:
        decision_id: Reference to the original Decision
        ruling: Final verdict ('proceed' | 'reject' | 'conditional')
        reasoning: Detailed explanation of the ruling rationale
        key_factors: Top factors that influenced the verdict
        confidence: Judge's confidence in the ruling [0.0-1.0]
        timestamp: When the verdict was delivered
    """

    decision_id: str
    ruling: Literal["proceed", "reject", "conditional"]
    reasoning: str
    key_factors: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Synthesis(BaseModel):
    """The Synthesis agent's improved version of the original idea.

    Takes the best arguments from both sides and produces a battle-tested
    version that addresses every objection the Defense raised while
    preserving the Prosecution's strongest points.

    Attributes:
        decision_id: Reference to the original Decision
        improved_idea: Full description of the enhanced idea (3-5 paragraphs)
        addressed_objections: How each Defense objection was addressed
        recommended_actions: Concrete next steps to implement
        strength_score: Overall strength of the improved idea [0.0-1.0]
        timestamp: When the synthesis was produced
    """

    decision_id: str
    improved_idea: str
    addressed_objections: list[str]
    recommended_actions: list[str]
    strength_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamEvent(BaseModel):
    """A real-time event streamed to the frontend via WebSocket.

    Each event has a type (matching the agent pipeline stage),
    an optional agent identifier, content text, and structured data.
    Events are serialized to JSON and sent over the WebSocket connection.

    Attributes:
        event_type: Pipeline stage identifier
        agent: Which agent produced this event
        content: Human-readable text content
        data: Structured data payload (agent output, claims, etc.)
        timestamp: When the event was generated
    """

    event_type: Literal[
        "research_start",
        "research_complete",
        "prosecutor_thinking",
        "prosecutor_complete",
        "defense_thinking",
        "defense_complete",
        "judge_start",
        "witness_spawned",
        "witness_complete",
        "cross_examination_complete",
        "verdict_start",
        "verdict_complete",
        "synthesis_start",
        "synthesis_complete",
        "error",
    ]
    agent: Optional[str] = None
    content: Optional[str] = None
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
