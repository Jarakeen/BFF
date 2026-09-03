from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
)


class CandidateRecommendationReason(str, Enum):
    """Why a Phase 12 comparison may or may not be recommended."""

    OBJECTIVE_IMPROVEMENT = "objective_improvement"
    HARD_CONSTRAINT_REPAIR = "hard_constraint_repair"
    BLOCKED = "blocked"
    UNRESOLVED = "unresolved"
    NOT_BETTER_THAN_BASELINE = "not_better_than_baseline"


@dataclass(frozen=True)
class ExplainedBuildChange:
    """Human-readable form of one immutable candidate change."""

    path: str
    before: Any
    after: Any
    source: str


@dataclass(frozen=True)
class BuildCandidateExplanation:
    """Structured Phase 12 explanation derived only from comparison evidence.

    This contract intentionally performs no ESO math and invents no score.  It
    exposes the immutable candidate changes, authoritative objective measurements,
    hard-constraint results, and unresolved evidence already carried by the
    comparison so every presentation layer can explain the same recommendation.
    """

    candidate_id: str
    candidate_source: str
    objective_name: str
    baseline_value: float | None
    candidate_value: float | None
    delta: float | None
    changes: tuple[ExplainedBuildChange, ...]
    constraints: tuple[CandidateConstraint, ...]
    unresolved: tuple[str, ...]
    evidence: tuple[str, ...]
    rejection_reason: str | None
    is_rankable: bool
    is_preferred: bool
    recommendation_reason: CandidateRecommendationReason

    @classmethod
    def from_comparison(
        cls,
        comparison: BuildCandidateComparison,
    ) -> "BuildCandidateExplanation":
        changes = tuple(
            ExplainedBuildChange(
                path=change.path,
                before=change.before,
                after=change.after,
                source=change.source,
            )
            for change in comparison.candidate.changes
        )

        if comparison.rejection_reason or comparison.blocking_constraints:
            reason = CandidateRecommendationReason.BLOCKED
        elif comparison.unresolved or comparison.delta is None:
            reason = CandidateRecommendationReason.UNRESOLVED
        elif comparison.is_constraint_repair:
            reason = CandidateRecommendationReason.HARD_CONSTRAINT_REPAIR
        elif comparison.is_improvement:
            reason = CandidateRecommendationReason.OBJECTIVE_IMPROVEMENT
        else:
            reason = CandidateRecommendationReason.NOT_BETTER_THAN_BASELINE

        return cls(
            candidate_id=comparison.candidate.candidate_id,
            candidate_source=comparison.candidate.candidate_source,
            objective_name=comparison.objective.value,
            baseline_value=comparison.baseline_value,
            candidate_value=comparison.candidate_value,
            delta=comparison.delta,
            changes=changes,
            constraints=tuple(comparison.constraints),
            unresolved=tuple(comparison.unresolved),
            evidence=tuple(comparison.evidence),
            rejection_reason=comparison.rejection_reason,
            is_rankable=comparison.is_rankable,
            is_preferred=comparison.is_preferred,
            recommendation_reason=reason,
        )
