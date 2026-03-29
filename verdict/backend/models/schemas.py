"""Pydantic v2 data models for the Verdict courtroom system."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
import uuid


class Decision(BaseModel):
    """A decision submitted for adversarial evaluation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    context: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Claim(BaseModel):
    """A single claim made by a Prosecutor or Defense agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    verified: Optional[bool] = None


class Argument(BaseModel):
    """A structured argument from either Prosecutor or Defense."""

    agent: Literal["prosecutor", "defense"]
    opening: str
    claims: list[Claim]
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WitnessReport(BaseModel):
    """A verification report from a specialist Witness agent."""

    claim_id: str
    witness_type: Literal["fact", "data", "precedent"]
    resolution: str
    confidence: float = Field(ge=0.0, le=1.0)
    verdict_on_claim: Literal["sustained", "overruled", "inconclusive"]

    @field_validator('verdict_on_claim', mode='before')
    @classmethod
    def normalize_verdict(cls, v):
        """Normalize LLM's free-form verdicts to valid enum values."""
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
    """Cross-examination results from the Judge."""

    contested_claims: list[str]
    witness_reports: list[WitnessReport]
    judge_notes: str


class VerdictResult(BaseModel):
    """The Judge's final ruling."""

    decision_id: str
    ruling: Literal["proceed", "reject", "conditional"]
    reasoning: str
    key_factors: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Synthesis(BaseModel):
    """The Synthesis agent's improved version of the original idea."""

    decision_id: str
    improved_idea: str
    addressed_objections: list[str]
    recommended_actions: list[str]
    strength_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamEvent(BaseModel):
    """A real-time event streamed to the frontend via WebSocket."""

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
