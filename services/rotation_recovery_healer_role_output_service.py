from __future__ import annotations

from typing import Protocol

from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
    RotationRuntimeBuildContextResolver,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)


class RotationRuntimeBindableHealerRoleOutput(Protocol):
    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
        *,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
    ) -> RotationCandidateRoleOutputEvidence: ...


class RotationRecoveryHealerRoleOutputService:
    """Evaluate healer output from the final stabilized candidate runtime timeline.

    Recovery stabilization may move casts or bar swaps. This adapter therefore binds
    exact-time runtime build context only after the final plan exists, using the
    snapshot-owned runtime CombatState resolver and the shared canonical rebuild
    bridge. Legacy snapshots without runtime history retain the role-output service's
    static-context path rather than inventing time-varying evidence.

    Runtime-bindable single-demand, multi-demand, and factory-result providers all use
    the same narrow protocol. This adapter owns neither healing math nor demand
    aggregation; it only binds final-plan runtime state before delegating to those
    existing authorities. The resolver is exposed so verified healer hard obligations
    can consume the exact same final-plan context as role output.
    """

    def __init__(
        self,
        *,
        build: PlayerBuild,
        role_output_service: RotationRuntimeBindableHealerRoleOutput,
        runtime_build_context_service: RotationPlanRuntimeBuildContextService,
    ) -> None:
        self.build = build
        self.role_output_service = role_output_service
        self.runtime_build_context_service = runtime_build_context_service

    def runtime_build_context_resolver_for_snapshot(
        self,
        snapshot: RecoveryHeavyStabilizedCandidateSnapshot,
    ) -> RotationRuntimeBuildContextResolver | None:
        runtime_state = snapshot.runtime_combat_state_resolver
        if runtime_state is None:
            return None

        def resolve(
            time_seconds: float,
            sequence: int | None = None,
        ):
            return self.runtime_build_context_service.resolve(
                self.build,
                runtime_combat_state_resolver=runtime_state,
                time_seconds=time_seconds,
                sequence=sequence,
            )

        return resolve

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
        runtime_resolver = self.runtime_build_context_resolver_for_snapshot(snapshot)
        if runtime_resolver is None:
            return self.role_output_service.evaluate_plan(candidate)
        return self.role_output_service.evaluate_plan(
            candidate,
            runtime_build_context_resolver=runtime_resolver,
        )


__all__ = [
    "RotationRecoveryHealerRoleOutputService",
    "RotationRuntimeBindableHealerRoleOutput",
]
