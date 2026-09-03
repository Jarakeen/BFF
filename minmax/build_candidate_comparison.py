from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.build_candidate import BuildCandidate
from minmax.evaluation_objective import EvaluationObjective


class ConstraintStatus(str, Enum):
    """Evidence-backed effect of a candidate on a required constraint."""

    PRESERVED = "preserved"
    IMPROVED = "improved"
    REPAIRED = "repaired"
    WORSENED = "worsened"
    UNSATISFIED = "unsatisfied"
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

    Callers supply measurements from authoritative engines. This contract only
    records their comparison and prevents a candidate with worsened or UNKNOWN
    hard constraints from being treated as rankable. A candidate may be preferred
    either because it improves the objective while preserving constraints or
    because it repairs a hard constraint the baseline itself violates.
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
            if constraint.status in (
                ConstraintStatus.WORSENED,
                ConstraintStatus.UNSATISFIED,
                ConstraintStatus.UNKNOWN,
            )
        )

    @property
    def repaired_constraints(self) -> tuple[CandidateConstraint, ...]:
        return tuple(
            constraint
            for constraint in self.constraints
            if constraint.status is ConstraintStatus.REPAIRED
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

    @property
    def is_constraint_repair(self) -> bool:
        return self.is_rankable and bool(self.repaired_constraints)

    @property
    def is_preferred(self) -> bool:
        """Return whether this candidate is a defensible recommendation over baseline."""

        return self.is_improvement or self.is_constraint_repair
