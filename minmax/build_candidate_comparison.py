from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.build_candidate import BuildCandidate
from minmax.evaluation_objective import EvaluationObjective


class ConstraintStatus(str, Enum):
    """Evidence-backed effect of a candidate on a required constraint."""

    PRESERVED = "preserved"
    IMPROVED = "improved"
    WORSENED = "worsened"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CandidateConstraint:
    """One sustain, coverage, responsibility, or other hard constraint result."""

    name: str
    status: ConstraintStatus
    explanation: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Candidate constraint name is required.")
        if not self.explanation.strip():
            raise ValueError("Candidate constraint explanation is required.")


@dataclass(frozen=True)
class BuildCandidateComparison:
    """Explainable baseline-vs-candidate outcome without embedding ESO math.

    Callers supply measurements from authoritative engines.  This contract only
    records their comparison and prevents a candidate with worsened or UNKNOWN
    hard constraints from being treated as a rankable improvement.
    """

    candidate: BuildCandidate
    objective: EvaluationObjective
    baseline_value: float | None
    candidate_value: float | None
    constraints: tuple[CandidateConstraint, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    rejection_reason: str | None = None

    @property
    def delta(self) -> float | None:
        if self.baseline_value is None or self.candidate_value is None:
            return None
        return self.candidate_value - self.baseline_value

    @property
    def blocking_constraints(self) -> tuple[CandidateConstraint, ...]:
        return tuple(
            constraint
            for constraint in self.constraints
            if constraint.status in (ConstraintStatus.WORSENED, ConstraintStatus.UNKNOWN)
        )

    @property
    def is_rankable(self) -> bool:
        return (
            self.candidate.is_evaluable
            and self.delta is not None
            and not self.blocking_constraints
            and not self.unresolved
            and not self.rejection_reason
        )

    @property
    def is_improvement(self) -> bool:
        delta = self.delta
        return self.is_rankable and delta is not None and delta > 0.0
