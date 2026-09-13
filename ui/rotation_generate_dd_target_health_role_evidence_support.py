from __future__ import annotations

"""Compose reviewed target-Health damage into the live DD Generate evidence path.

This support is additive over ``RotationGenerateDDRoleEvidenceSupport``. All existing
LA/HA/Ultimate, periodic-runtime, target-state, resistance, sustain, and role-ranking
composition remains owned by the base support. The only changed seam is skill damage:
a canonical bar-aware skill evaluator is wrapped with reviewed periodic target-Health
support when the registry, exact target snapshot resolver, and target identity are all
explicitly available.

An explicit constructor resolver/identity takes precedence. Otherwise a canonical
encounter Health trajectory already retained on the evidence bundle is adapted into an
exact snapshot resolver using the selected encounter id as target identity. The
production semantics registry remains empty by default, so no real periodic execute is
made executable until reviewed skill evidence is added.
"""

from dataclasses import replace

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_action_damage_evidence_service import (
    RotationActionDamageProvider,
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationCandidateDDRoleOutputService,
)
from services.rotation_candidate_periodic_target_health_damage_bridge_service import (
    RotationCandidatePeriodicTargetHealthDamageBridgeService,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_candidate_target_health_aware_skill_damage_factory_service import (
    RotationCandidateTargetHealthAwareSkillDamageFactoryService,
    RotationRuntimeTargetSnapshotResolver,
)
from services.rotation_candidate_ultimate_damage_evidence_service import (
    RotationCandidateUltimateDamageEvidenceService,
)
from services.rotation_dd_periodic_target_health_semantics_registry_service import (
    RotationDDPeriodicTargetHealthSemanticsRegistryService,
)
from services.rotation_periodic_target_health_eligibility_service import (
    RotationPeriodicTargetHealthEligibilityService,
)
from services.rotation_periodic_target_health_semantics_service import (
    RotationPeriodicTargetHealthSemanticsService,
)
from services.rotation_target_health_trajectory_snapshot_service import (
    RotationTargetHealthTrajectorySnapshotService,
)
from ui import rotation_generate_dd_role_evidence_support as base_support


class _RotationGenerateTargetHealthBarAwareSkillDamageProvider(
    base_support._RotationGenerateBarAwareSkillDamageProvider
):
    """Build the ordinary exact-bar evaluator, then add reviewed Health semantics."""

    def __init__(
        self,
        *,
        periodic_target_health_semantics,
        runtime_target_snapshot_resolver: RotationRuntimeTargetSnapshotResolver | None,
        target_identity: str | None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.periodic_target_health_semantics = tuple(periodic_target_health_semantics)
        self.runtime_target_snapshot_resolver = runtime_target_snapshot_resolver
        self.target_identity = str(target_identity or "").strip()

    def evaluate_action(self, *, candidate, action: RotationAction) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.SKILL:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} damage requires its dedicated canonical action evaluator",
                ),
            )

        if self.runtime_build_context_resolver is not None:
            runtime = self.runtime_build_context_resolver(
                float(action.time_seconds),
                int(action.sequence),
            )
            if not runtime.resolved or runtime.context is None:
                unresolved = tuple(
                    dict.fromkeys(
                        str(message).strip()
                        for message in runtime.unresolved
                        if str(message).strip()
                    )
                ) or ("runtime skill build context is unresolved",)
                return RotationActionDamageEvidence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=None,
                    unresolved=unresolved,
                )
            context = runtime.context
        else:
            resolver = base_support.RotationActiveBarContextResolverService(
                static_context=self.static_context,
                plan=candidate.plan,
            )
            context = resolver.context_at(action.time_seconds, action.sequence)

        context = replace(
            context,
            target_resistance=base_support._target_resistance_at(
                self.runtime_target_resistance_resolver,
                fallback=self.target_resistance,
                action=action,
            ),
            fight_duration=float(candidate.plan.duration_seconds),
        )
        base = RotationCandidateSkillDamageEvidenceService(
            database_path=self.database_path,
            context=context,
            target_combat_state=base_support._target_state_at(
                self.runtime_target_combat_state_resolver,
                action,
            ),
            periodic_runtime_projection_service=self.periodic_runtime_projection_service,
            periodic_runtime_semantics=self.periodic_runtime_semantics,
            runtime_build_context_resolver=self.runtime_build_context_resolver,
            runtime_target_combat_state_resolver=self.runtime_target_combat_state_resolver,
            runtime_target_resistance_resolver=self.runtime_target_resistance_resolver,
            runtime_target_snapshot_resolver=self.runtime_target_snapshot_resolver,
            execute_target_identity=self.target_identity,
        )
        provider = RotationCandidateTargetHealthAwareSkillDamageFactoryService(
            semantics=self.periodic_target_health_semantics,
            snapshot_resolver=self.runtime_target_snapshot_resolver,
            target_identity=self.target_identity,
        ).wrap(base)
        return provider.evaluate_action(candidate=candidate, action=action)


class RotationGenerateDDTargetHealthRoleEvidenceSupport(
    base_support.RotationGenerateDDRoleEvidenceSupport
):
    """Live DD Generate support with optional reviewed target-Health evidence."""

    def __init__(
        self,
        *,
        periodic_target_health_semantics_registry: (
            RotationDDPeriodicTargetHealthSemanticsRegistryService | None
        ) = None,
        runtime_target_snapshot_resolver: RotationRuntimeTargetSnapshotResolver | None = None,
        target_identity: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.periodic_target_health_semantics_registry = (
            periodic_target_health_semantics_registry
            or RotationDDPeriodicTargetHealthSemanticsRegistryService()
        )
        self.runtime_target_snapshot_resolver = runtime_target_snapshot_resolver
        self.target_identity = str(target_identity or "").strip()

    def _target_health_inputs(self, evidence_bundle):
        resolver = self.runtime_target_snapshot_resolver
        identity = self.target_identity
        trajectory = getattr(evidence_bundle, "target_health_trajectory", None)

        if resolver is None and trajectory is not None:
            if not identity:
                identity = str(getattr(evidence_bundle, "encounter_id", "") or "").strip()
            if identity:
                resolver = RotationTargetHealthTrajectorySnapshotService(
                    trajectory=trajectory,
                    target_identity=identity,
                ).snapshot_at

        return resolver, identity

    def _build_plan_evidence_provider(
        self,
        *,
        player_build,
        evidence_bundle,
        static_context,
        target_resistance: float,
        periodic_runtime_semantics,
        runtime_build_context_resolver,
        runtime_target_combat_state_resolver,
        runtime_target_resistance_resolver,
        activation_anchor_resolver,
    ):
        runtime_target_snapshot_resolver, target_identity = self._target_health_inputs(
            evidence_bundle
        )
        skill_provider = _RotationGenerateTargetHealthBarAwareSkillDamageProvider(
            database_path=self.database_path,
            static_context=static_context,
            target_resistance=target_resistance,
            periodic_runtime_semantics=periodic_runtime_semantics,
            runtime_build_context_resolver=runtime_build_context_resolver,
            runtime_target_combat_state_resolver=runtime_target_combat_state_resolver,
            runtime_target_resistance_resolver=runtime_target_resistance_resolver,
            activation_anchor_resolver=activation_anchor_resolver,
            periodic_target_health_semantics=(
                self.periodic_target_health_semantics_registry.load()
            ),
            runtime_target_snapshot_resolver=runtime_target_snapshot_resolver,
            target_identity=target_identity,
        )
        ultimate_provider = RotationCandidateUltimateDamageEvidenceService(
            skill_damage_delegate=skill_provider,
        )

        light_attack_provider: RotationActionDamageProvider | None = None
        heavy_attack_provider: RotationActionDamageProvider | None = None
        if self.weapon_attack_provider_factory is not None:
            light_attack_provider, heavy_attack_provider = (
                self.weapon_attack_provider_factory.providers_for(
                    player_build=player_build,
                    static_context=static_context,
                    target_resistance=target_resistance,
                    runtime_build_context_resolver=runtime_build_context_resolver,
                    runtime_target_combat_state_resolver=runtime_target_combat_state_resolver,
                    runtime_target_resistance_resolver=runtime_target_resistance_resolver,
                )
            )

        action_router = RotationCandidateActionDamageEvidenceService(
            skill_provider=skill_provider,
            light_attack_provider=light_attack_provider,
            heavy_attack_provider=heavy_attack_provider,
            ultimate_provider=ultimate_provider,
        )
        role_output = RotationCandidateDDRoleOutputService(
            action_damage_evidence_provider=action_router,
        )
        return RotationCandidateCanonicalPlanEvidenceService(
            build=player_build,
            resource=evidence_bundle.resource,
            role_output_evidence_provider=role_output,
        )


__all__ = ["RotationGenerateDDTargetHealthRoleEvidenceSupport"]
