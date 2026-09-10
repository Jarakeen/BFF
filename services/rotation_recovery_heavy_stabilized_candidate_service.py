from __future__ import annotations

from dataclasses import dataclass

from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationResult,
)


@dataclass(frozen=True)
class RotationRecoveryHeavyStabilizedCandidateResult:
    """Expose a fixed-point heavy schedule to the modern candidate pipeline.

    ``candidate`` is deliberately absent when stabilization did not converge. The
    stabilization result remains available for diagnostics so iteration-limit or
    other termination evidence is never discarded merely because downstream code
    prefers a ``GeneratedRotationCandidate``.
    """

    stabilization: RotationRecoveryHeavyStabilizationResult
    candidate: GeneratedRotationCandidate | None

    @property
    def recommendable(self) -> bool:
        return self.candidate is not None


class RotationRecoveryHeavyStabilizedCandidateService:
    """Translate one stabilized recovery-heavy policy into a generated candidate.

    Heavy placement remains owned by ``RotationRecoveryHeavyStabilizationService``.
    This adapter owns no sustain, timing, bar, restoration, or obligation mechanics.
    It only carries the final converged plan back into the candidate/recommendation
    pipeline while preserving the caller's existing policy identity.

    A converged plan may still fail hard gameplay obligations; that is intentionally
    left to the existing candidate scorecard/ranking path. A non-converged plan is
    not exposed as a candidate at all, preventing an iteration-limit snapshot from
    being mistaken for a stable recommendation input.
    """

    @staticmethod
    def from_stabilization(
        *,
        candidate_id: str,
        stabilization: RotationRecoveryHeavyStabilizationResult,
        refresh_leads: tuple[DemandRefreshLead, ...] = (),
        action_claims: tuple[DemandActionClaim, ...] = (),
    ) -> RotationRecoveryHeavyStabilizedCandidateResult:
        resolved_id = str(candidate_id or "").strip()
        if not resolved_id:
            raise ValueError("stabilized recovery-heavy candidate_id is required")

        if not stabilization.converged:
            return RotationRecoveryHeavyStabilizedCandidateResult(
                stabilization=stabilization,
                candidate=None,
            )

        candidate = GeneratedRotationCandidate(
            candidate_id=resolved_id,
            plan=stabilization.plan,
            refresh_leads=tuple(refresh_leads),
            action_claims=tuple(action_claims),
        )
        return RotationRecoveryHeavyStabilizedCandidateResult(
            stabilization=stabilization,
            candidate=candidate,
        )


__all__ = [
    "RotationRecoveryHeavyStabilizedCandidateResult",
    "RotationRecoveryHeavyStabilizedCandidateService",
]
