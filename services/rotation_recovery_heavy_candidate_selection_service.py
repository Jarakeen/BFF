from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationResult,
)


class RecoveryFinalCandidateEvaluation(Protocol):
    """Minimal canonical ranking evidence required for final selection."""

    candidate_id: str
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RecoveryStabilizedCandidateInput:
    """Join canonical candidate ranking to its recovery fixed-point result."""

    evaluation: RecoveryFinalCandidateEvaluation
    stabilization: RotationRecoveryHeavyStabilizationResult

    def __post_init__(self) -> None:
        candidate_id = str(self.evaluation.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("recovery stabilized candidate_id must be non-empty")
        if int(self.evaluation.rank) <= 0:
            raise ValueError("recovery stabilized candidate rank must be positive")


@dataclass(frozen=True)
class RecoveryStabilizedCandidateSelectionResult:
    candidate_id: str
    evaluation: RecoveryFinalCandidateEvaluation
    stabilization: RotationRecoveryHeavyStabilizationResult
    selectable: bool
    rank: int
    reasons: tuple[str, ...]


class RotationRecoveryHeavyCandidateSelectionService:
    """Select only candidates that are both canonically eligible and recovery-valid.

    Candidate ranking and recovery stabilization answer different questions. The
    canonical evaluator decides whether the plan satisfies its supplied encounter,
    support, effect, timing, and resource obligations. Recovery stabilization then
    decides whether iterative heavy insertion reached a deterministic valid fixed
    point. Final Rotation Maker selection must require both facts.

    A stable-but-invalid result (``stable_no_legal_improvement``) stays visible for
    diagnostics but cannot outrank a valid candidate. An iteration-limit result is
    likewise non-selectable even if its last canonical evaluation happened to be
    eligible, because the execution schedule has not stabilized.
    """

    def rank(
        self,
        candidates: tuple[RecoveryStabilizedCandidateInput, ...],
    ) -> tuple[RecoveryStabilizedCandidateSelectionResult, ...]:
        seen: set[str] = set()
        staged: list[tuple[tuple[object, ...], RecoveryStabilizedCandidateSelectionResult]] = []

        for candidate in candidates:
            candidate_id = str(candidate.evaluation.candidate_id).strip()
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate recovery stabilized candidate_id: {candidate_id!r}"
                )
            seen.add(key)

            selectable = self._is_selectable(candidate)
            result = RecoveryStabilizedCandidateSelectionResult(
                candidate_id=candidate_id,
                evaluation=candidate.evaluation,
                stabilization=candidate.stabilization,
                selectable=selectable,
                rank=0,
                reasons=self._reasons(candidate, selectable=selectable),
            )
            staged.append(
                (
                    (
                        0 if selectable else 1,
                        int(candidate.evaluation.rank),
                        candidate_id.casefold(),
                    ),
                    result,
                )
            )

        staged.sort(key=lambda item: item[0])
        return tuple(
            RecoveryStabilizedCandidateSelectionResult(
                candidate_id=result.candidate_id,
                evaluation=result.evaluation,
                stabilization=result.stabilization,
                selectable=result.selectable,
                rank=index + 1,
                reasons=result.reasons,
            )
            for index, (_key, result) in enumerate(staged)
        )

    def select_best(
        self,
        candidates: tuple[RecoveryStabilizedCandidateInput, ...],
    ) -> RecoveryStabilizedCandidateSelectionResult | None:
        return next((item for item in self.rank(candidates) if item.selectable), None)

    @staticmethod
    def _is_selectable(candidate: RecoveryStabilizedCandidateInput) -> bool:
        stabilization = candidate.stabilization
        return (
            candidate.evaluation.tier is RotationCandidateTier.ELIGIBLE
            and stabilization.converged
            and stabilization.termination_reason == "stable_fixed_point"
            and stabilization.tracked_hard_obligations_satisfied
        )

    @staticmethod
    def _reasons(
        candidate: RecoveryStabilizedCandidateInput,
        *,
        selectable: bool,
    ) -> tuple[str, ...]:
        reasons = list(candidate.evaluation.reasons)
        stabilization = candidate.stabilization

        if stabilization.termination_reason == "stable_no_legal_improvement":
            reasons.append(
                "recovery schedule stabilized with unresolved hard obligations; "
                "no legal improvement was found"
            )
        elif stabilization.termination_reason == "iteration_limit_reached":
            reasons.append(
                "recovery schedule did not reach a deterministic fixed point before "
                "the iteration limit"
            )
        elif not stabilization.tracked_hard_obligations_satisfied:
            reasons.append("recovery schedule retains tracked hard obligation failures")

        if (
            not selectable
            and candidate.evaluation.tier is RotationCandidateTier.ELIGIBLE
            and stabilization.termination_reason == "stable_fixed_point"
            and stabilization.tracked_hard_obligations_satisfied
        ):
            reasons.append("recovery candidate is not selectable")

        return tuple(reasons)


__all__ = [
    "RecoveryFinalCandidateEvaluation",
    "RecoveryStabilizedCandidateInput",
    "RecoveryStabilizedCandidateSelectionResult",
    "RotationRecoveryHeavyCandidateSelectionService",
]
