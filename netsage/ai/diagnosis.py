from dataclasses import dataclass
from typing import Literal


ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


@dataclass
class Diagnosis:
    likely_root_cause: str
    osi_layer: str
    confidence: ConfidenceLevel
    evidence: list[str]
    next_command: str
    fix_steps: list[str]
    verification_steps: list[str]
