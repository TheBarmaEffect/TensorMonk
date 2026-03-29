"""Agent module — six specialized LLM agents for adversarial decision analysis.

Architecture:
    ResearchAgent → produces anonymous research package (authorship stripped)
    ProsecutorAgent → argues FOR the decision (constitutionally bound)
    DefenseAgent → argues AGAINST the decision (constitutionally bound)
    JudgeAgent → cross-examines, spawns witnesses, delivers verdict
    WitnessAgent → fact/data/precedent verification of contested claims
    SynthesisAgent → produces battle-tested improved version of the original idea

Isolation constraints:
    - Prosecutor and Defense run in parallel, NEVER see each other's output
    - Research authorship metadata is stripped via strip_authorship() before
      reaching Prosecutor/Defense (authorship blindness)
    - Judge is the first node to see both prosecution and defense arguments
    - Witnesses are spawned dynamically based on contested claims
    - All agents output Pydantic-validated structured data
"""

from .research import ResearchAgent
from .prosecutor import ProsecutorAgent
from .defense import DefenseAgent
from .judge import JudgeAgent
from .witness import WitnessAgent
from .synthesis import SynthesisAgent

__all__ = [
    "ResearchAgent",
    "ProsecutorAgent",
    "DefenseAgent",
    "JudgeAgent",
    "WitnessAgent",
    "SynthesisAgent",
]
