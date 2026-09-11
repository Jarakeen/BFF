from __future__ import annotations

from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerRoleOutputService,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)


class RotationRecoveryHealerRoleOutputService:
    """Evaluate healer output from the final stabilized candidate runtime timeline.

    Recovery stabilization may move casts or bar swaps. This adapter therefore binds
    exact-time runtime build context only after the final plan exists, using the
    snapshot-owned runtime CombatState resolver and the shared canonical rebuild
    bridge. Legacy snapshots without runtime history retain the role-output service's
    static-context path rather than inventing time-varying evidence.
    """

    def __init__(
        self,
        *,
        build: PlayerBuild,
        role_output_service: RotationCandidateHealerRoleOutputService,
        runtime_build_context_service: RotationPlanRuntimeBuildContextService,
    ) -> None:
        self.build = build
        self.role_output_service = role_output_service
        self.runtime_build_context_service = runtime_build_context_service

    def evaluate_snapshot(
        self,
        snapshot: RecoveryHeavyStabilizedCandidateSnapshot,
    ) -> RotationCandidateRoleOutputEvidence:
        candidate = GeneratedRotationCandidate(
            candidate_id=snapshot.candidate_id,
            plan=snapshot.plan,
            refresh_leads=(),
            action_claims=(),
        )
        runtime_state = snapshot.runtime_combat_state_resolver
        if runtime_state is None:
            return self.role_output_service.evaluate_plan(candidate)

        def runtime_build_context_resolver(
            time_seconds: float,
            sequence: int | None = None,
        ):
            return self.runtime_build_context_service.resolve(
                self.build,
                runtime_combat_state_resolver=runtime_state,
                time_seconds=time_seconds,
                sequence=sequence,
            )

        return self.role_output_service.evaluate_plan(
            candidate,
            runtime_build_context_resolver=runtime_build_context_resolver,
        )


__all__ = ["RotationRecoveryHealerRoleOutputService"]
