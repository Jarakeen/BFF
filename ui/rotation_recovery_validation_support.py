from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RotationRecoveryHeavyCandidateOrchestrationResult,
)
from ui.rotation_generation_support import RotationGenerationResult


class RotationRecoveryValidationScope(str, Enum):
    """How much evidence has actually validated a generated recovery schedule."""

    NOT_EVALUATED = "not_evaluated"
    RESOURCE_ONLY = "resource_only"
    CANONICAL_CANDIDATE = "canonical_candidate"


@dataclass(frozen=True)
class RotationRecoveryValidationEvidence:
    """Application-facing truth about recovery validation and selectability.

    ``selectable`` is intentionally tri-state. ``None`` means the available
    evidence is insufficient to answer whether the rotation is canonically valid.
    Resource-only fixed-point stabilization can therefore never be mistaken for
    full candidate validation merely because it converged.
    """

    scope: RotationRecoveryValidationScope
    selectable: bool | None
    selected_candidate_id: str | None = None
    reasons: tuple[str, ...] = ()

    @property
    def canonically_evaluated(self) -> bool:
        return self.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE


class RotationRecoveryValidationSupport:
    """Classify old single-plan recovery evidence versus the canonical pipeline.

    The legacy UI generation path can stabilize a schedule against replayed resource
    pressure, but it does not evaluate the candidate hard-obligation/effect family.
    Its result is therefore explicitly ``RESOURCE_ONLY`` and has unknown canonical
    selectability. The candidate pipeline is the only source accepted here for a
    definitive selectable/non-selectable answer.
    """

    @staticmethod
    def from_generation_result(
        result: RotationGenerationResult,
    ) -> RotationRecoveryValidationEvidence:
        if result.recovery_stabilization is None:
            return RotationRecoveryValidationEvidence(
                scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                selectable=None,
                reasons=(
                    "recovery stabilization was not evaluated for this generated plan",
                ),
            )

        stabilization = result.recovery_stabilization
        termination = str(getattr(stabilization, "termination_reason", "") or "").strip()
        reasons = [
            "recovery was stabilized against resource pressure only; canonical "
            "candidate hard obligations and build-specific effect uptime were not evaluated"
        ]
        if termination:
            reasons.append(f"resource-only recovery termination: {termination}")
        return RotationRecoveryValidationEvidence(
            scope=RotationRecoveryValidationScope.RESOURCE_ONLY,
            selectable=None,
            reasons=tuple(reasons),
        )

    @staticmethod
    def from_candidate_pipeline_result(
        result: RotationRecoveryHeavyCandidateOrchestrationResult,
    ) -> RotationRecoveryValidationEvidence:
        selected = result.selected_candidate
        if selected is not None:
            return RotationRecoveryValidationEvidence(
                scope=RotationRecoveryValidationScope.CANONICAL_CANDIDATE,
                selectable=True,
                selected_candidate_id=selected.candidate_id,
                reasons=tuple(selected.reasons),
            )

        diagnostic_reasons: list[str] = []
        for candidate in result.ranked_candidates:
            diagnostic_reasons.extend(
                f"{candidate.candidate_id}: {reason}"
                for reason in candidate.reasons
            )
        if not diagnostic_reasons:
            diagnostic_reasons.append(
                "canonical candidate evaluation returned no selectable rotation"
            )
        return RotationRecoveryValidationEvidence(
            scope=RotationRecoveryValidationScope.CANONICAL_CANDIDATE,
            selectable=False,
            reasons=tuple(diagnostic_reasons),
        )


__all__ = [
    "RotationRecoveryValidationEvidence",
    "RotationRecoveryValidationScope",
    "RotationRecoveryValidationSupport",
]
