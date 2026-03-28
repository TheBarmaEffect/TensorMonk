cat << 'EOF' > app/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class Decision(BaseModel):
    id: str
    question: str
    context: Optional[str]
    created_at: datetime

class ResearchPackage(BaseModel):
    decision_id: str
    facts: List[str]
    sources: List[str]
    context_summary: str

class Claim(BaseModel):
    statement: str
    evidence: str
    confidence: float
    verified: Optional[bool] = None

class Argument(BaseModel):
    agent: Literal["prosecutor", "defense"]
    claims: List[Claim]
    confidence: float
    timestamp: datetime

class Verdict(BaseModel):
    decision_id: str
    ruling: Literal["proceed", "reject", "conditional"]
    reasoning: str
    key_factors: List[str]
    confidence: float
    timestamp: datetime
EOF