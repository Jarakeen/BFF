from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Protocol

from engine.config import get_data_dir
from minmax.build_candidate_damage import calculation_result_from_build_context
from minmax.build_evaluation import BuildEvaluation
from minmax.combat_state import CombatState
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationAction, RotationActionKind
from models.build_model import PlayerBuild
from services.rotation_active_bar_context_resolver_service import (
    RotationActiveBarContextResolverService,
)
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
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_heavy_attack_damage_evidence_service import (
    RotationCandidateHeavyAttackDamageEvidenceService,
)
from services.rotation_candidate_light_attack_damage_evidence_service import (
    RotationCandidateLightAttackDamageEvidenceService,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchorResolver,
    RotationCandidatePeriodicDamageRuntimeProjectionService,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationCandidatePeriodicDamageTimingEvidenceService,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_candidate_ultimate_damage_evidence_service import (
    RotationCandidateUltimateDamageEvidenceService,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
    RotationRuntimeBuildContextResolver,
)
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationSavedBuildWeaponAttackEvaluationService,
    RotationWeaponAttackBuildEvaluationResolution,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage_dealer"}


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class RotationRuntimeTargetCombatStateResolver(Protocol):
    """Resolve authoritative target-side combat state at one exact runtime point."""

    def __call__(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> CombatState: ...


def _target_state_at(
    resolver: RotationRuntimeTargetCombatStateResolver | None,
    action: RotationAction,
) -> CombatState | None:
    if resolver is None:
        return None
    return resolver(action.time_seconds, action.sequence)


def _weapon_attack_evaluation_at(
    *,
    evaluation: RotationWeaponAttackBuildEvaluationResolution,
    static_context,
    candidate: GeneratedRotationCandidate,
    action: RotationAction,
    runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None,
) -> tuple[BuildEvaluation | None, object | None, tuple[str, ...]]:
    """Resolve one LA/HA evaluation from the exact canonical action-time context."""

    if runtime_build_context_resolver is not None:
        runtime = runtime_build_context_resolver(
            action.time_seconds,
            action.sequence,
        )
        if not runtime.resolved or runtime.context is None:
            unresolved = tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in runtime.unresolved
                    if str(message).strip()
                )
            ) or ("runtime weapon-attack build context is unresolved",)
            return None, None, unresolved
        context = runtime.context
        active_bar = runtime.active_bar
    else:
        resolver = RotationActiveBarContextResolverService(
            static_context=static_context,
            plan=candidate.plan,
        )
        context = resolver.context_at(action.time_seconds, action.sequence)
        active_bar = context.active_bar

    base_evaluation = evaluation.evaluation_for(active_bar)
    if base_evaluation is None:
        return (
            None,
            context,
            (f"{active_bar} canonical weapon-attack BuildEvaluation is unavailable",),
        )

    calculation = calculation_result_from_build_context(context)
    if calculation is None:
        return (
            None,
            context,
            (
                f"{active_bar} weapon-attack evaluation requires resolved canonical core stats",
            ),
        )

    return replace(base_evaluation, stats=calculation), context, ()


class RotationGenerateDDWeaponAttackProviderFactory(Protocol):
    """Supply verified LA/HA evaluators from one canonical saved-build evaluation."""

    def providers_for(
        self,
        *,
        player_build: PlayerBuild,
        static_context,
        target_resistance: float,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
        runtime_target_combat_state_resolver: RotationRuntimeTargetCombatStateResolver | None = None,
    ) -> tuple[
        RotationActionDamageProvider | None,
        RotationActionDamageProvider | None,
    ]: ...


class _RotationGenerateBarAwareSkillDamageProvider:
    """Evaluate one skill against the canonical context active at its exact plan point."""

    def __init__(
        self,
        *,
        database_path: Path,
        static_context,
        target_resistance: float,
        periodic_runtime_semantics: tuple[
            RotationPeriodicDamageRuntimeSemantics, ...
        ] = (),
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
        runtime_target_combat_state_resolver: RotationRuntimeTargetCombatStateResolver | None = None,
        activation_anchor_resolver: PeriodicDamageActivationAnchorResolver | None = None,
    ) -> None:
        self.database_path = database_path
        self.static_context = static_context
        self.target_resistance = float(target_resistance)
        self.periodic_runtime_semantics = tuple(periodic_runtime_semantics)
        self.runtime_build_context_resolver = runtime_build_context_resolver
        self.runtime_target_combat_state_resolver = runtime_target_combat_state_resolver
        self.activation_anchor_resolver = activation_anchor_resolver
        self.periodic_runtime_projection_service = (
            RotationCandidatePeriodicDamageRuntimeProjectionService(
                RotationCandidatePeriodicDamageTimingEvidenceService(database_path),
                activation_anchor_resolver=activation_anchor_resolver,
            )
            if self.periodic_runtime_semantics
            else None
        )

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.SKILL:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} damage requires its dedicated canonical action evaluator",
                ),
            )

        resolver = RotationActiveBarContextResolverService(
            static_context=self.static_context,
            plan=candidate.plan,
        )
        context = resolver.context_at(action.time_seconds, action.sequence)
        context = replace(
            context,
            target_resistance=self.target_resistance,
            fight_duration=float(candidate.plan.duration_seconds),
        )
        return RotationCandidateSkillDamageEvidenceService(
            database_path=self.database_path,
            context=context,
            target_combat_state=_target_state_at(
                self.runtime_target_combat_state_resolver,
                action,
            ),
            periodic_runtime_projection_service=self.periodic_runtime_projection_service,
            periodic_runtime_semantics=self.periodic_runtime_semantics,
            runtime_build_context_resolver=self.runtime_build_context_resolver,
        ).evaluate_action(
            candidate=candidate,
            action=action,
        )


class _RotationGenerateBarAwareLightAttackDamageProvider:
    """Evaluate each light attack from the exact canonical state active on its bar."""

    def __init__(
        self,
        *,
        evaluation: RotationWeaponAttackBuildEvaluationResolution,
        static_context,
        target_resistance: float,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
        runtime_target_combat_state_resolver: RotationRuntimeTargetCombatStateResolver | None = None,
    ) -> None:
        if not evaluation.resolved or evaluation.build is None:
            raise ValueError(
                "bar-aware light-attack provider requires resolved weapon-attack evaluation"
            )
        self.evaluation = evaluation
        self.static_context = static_context
        self.target_resistance = float(target_resistance)
        self.runtime_build_context_resolver = runtime_build_context_resolver
        self.runtime_target_combat_state_resolver = runtime_target_combat_state_resolver

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.LIGHT_ATTACK:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} is not a light attack for light-attack damage evaluation",
                ),
            )

        build_evaluation, context, unresolved = _weapon_attack_evaluation_at(
            evaluation=self.evaluation,
            static_context=self.static_context,
            candidate=candidate,
            action=action,
            runtime_build_context_resolver=self.runtime_build_context_resolver,
        )
        if build_evaluation is None or context is None:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=unresolved,
            )

        return RotationCandidateLightAttackDamageEvidenceService(
            build=self.evaluation.build,
            evaluation=build_evaluation,
            initial_bar="front",
            evaluation_context=EvaluationContext(
                fight_duration=float(candidate.plan.duration_seconds),
                target_resistance=self.target_resistance,
            ),
            attacker_combat_state=getattr(context, "combat_state", None),
            target_combat_state=_target_state_at(
                self.runtime_target_combat_state_resolver,
                action,
            ),
        ).evaluate_action(
            candidate=candidate,
            action=action,
        )


class _RotationGenerateBarAwareHeavyAttackDamageProvider:
    """Evaluate only scheduler-verified fully charged heavies on their exact runtime bar."""

    def __init__(
        self,
        *,
        evaluation: RotationWeaponAttackBuildEvaluationResolution,
        static_context,
        target_resistance: float,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
        runtime_target_combat_state_resolver: RotationRuntimeTargetCombatStateResolver | None = None,
    ) -> None:
        if not evaluation.resolved or evaluation.build is None:
            raise ValueError(
                "bar-aware heavy-attack provider requires resolved weapon-attack evaluation"
            )
        self.evaluation = evaluation
        self.static_context = static_context
        self.target_resistance = float(target_resistance)
        self.runtime_build_context_resolver = runtime_build_context_resolver
        self.runtime_target_combat_state_resolver = runtime_target_combat_state_resolver

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.HEAVY_ATTACK:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} is not a heavy attack for heavy-attack damage evaluation",
                ),
            )

        build_evaluation, context, unresolved = _weapon_attack_evaluation_at(
            evaluation=self.evaluation,
            static_context=self.static_context,
            candidate=candidate,
            action=action,
            runtime_build_context_resolver=self.runtime_build_context_resolver,
        )
        if build_evaluation is None or context is None:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=unresolved,
            )

        completion_evidence = (
            RotationHeavySustainProjectionService.completion_evidence_from_verified_reservations(
                candidate.plan
            )
        )
        return RotationCandidateHeavyAttackDamageEvidenceService(
            build=self.evaluation.build,
            evaluation=build_evaluation,
            initial_bar="front",
            completion_evidence=completion_evidence,
            evaluation_context=EvaluationContext(
                fight_duration=float(candidate.plan.duration_seconds),
                target_resistance=self.target_resistance,
            ),
            attacker_combat_state=getattr(context, "combat_state", None),
            target_combat_state=_target_state_at(
                self.runtime_target_combat_state_resolver,
                action,
            ),
        ).evaluate_action(
            candidate=candidate,
            action=action,
        )


class _RotationGenerateUnresolvedWeaponAttackProvider:
    """Preserve bridge failures as action-local unresolved evidence."""

    def __init__(self, unresolved: tuple[str, ...]) -> None:
        self.unresolved = tuple(
            dict.fromkeys(
                str(item).strip() for item in unresolved if str(item).strip()
            )
        ) or ("canonical weapon-attack evaluation is unresolved",)

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=self.unresolved,
        )


class RotationGenerateDDCanonicalWeaponAttackProviderFactory:
    """Production bridge from saved-build canonical state to weapon-attack providers."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        evaluation_service: RotationSavedBuildWeaponAttackEvaluationService | None = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.evaluation_service = (
            evaluation_service
            or RotationSavedBuildWeaponAttackEvaluationService(self.database_path)
        )

    def providers_for(
        self,
        *,
        player_build: PlayerBuild,
        static_context,
        target_resistance: float,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
        runtime_target_combat_state_resolver: RotationRuntimeTargetCombatStateResolver | None = None,
    ) -> tuple[
        RotationActionDamageProvider | None,
        RotationActionDamageProvider | None,
    ]:
        resolution = self.evaluation_service.resolve(
            player_build=player_build,
            static_context=static_context,
        )
        if not resolution.resolved:
            unresolved = _RotationGenerateUnresolvedWeaponAttackProvider(
                resolution.unresolved
            )
            return unresolved, unresolved
        return (
            _RotationGenerateBarAwareLightAttackDamageProvider(
                evaluation=resolution,
                static_context=static_context,
                target_resistance=target_resistance,
                runtime_build_context_resolver=runtime_build_context_resolver,
                runtime_target_combat_state_resolver=runtime_target_combat_state_resolver,
            ),
            _RotationGenerateBarAwareHeavyAttackDamageProvider(
                evaluation=resolution,
                static_context=static_context,
                target_resistance=target_resistance,
                runtime_build_context_resolver=runtime_build_context_resolver,
                runtime_target_combat_state_resolver=runtime_target_combat_state_resolver,
            ),
        )


class _RotationGenerateSnapshotAwarePlanEvidenceProvider:
    """Use static evidence normally and bind runtime evidence only after stabilization."""

    def __init__(self, *, static_provider, runtime_provider_factory) -> None:
        self.static_provider = static_provider
        self.runtime_provider_factory = runtime_provider_factory

    @property
    def role_output_evidence_provider(self):
        """Preserve the canonical plan-evidence compatibility surface."""

        return self.static_provider.role_output_evidence_provider

    def evaluate_plan(self, candidate: GeneratedRotationCandidate):
        return self.static_provider.evaluate_plan(candidate)

    def for_stabilized_snapshot(self, snapshot):
        if (
            snapshot.runtime_combat_state_resolver is None
            and getattr(snapshot, "runtime_target_combat_state_resolver", None) is None
            and getattr(snapshot, "runtime_activation_anchor_resolver", None) is None
        ):
            return self.static_provider
        return self.runtime_provider_factory(snapshot)


class RotationGenerateDDRoleEvidenceSupport:
    """Compose fail-closed canonical DD role output for Generate candidates.

    Direct skills, Ultimates, LA, and verified completed HA use their existing
    canonical evaluators. Reviewed periodic semantics come from the production DD
    runtime registry. Snapshot DoTs reuse cast-time magnitude only when explicitly
    reviewed as such. Dynamic DoTs bind to the final stabilized candidate's runtime
    combat-state resolver and rebuild exact-time calculation context for every tick.
    Stabilized LA/HA evidence uses that same exact runtime build-context resolver so
    temporal resource/stat/bar state does not collapse back to static build values.
    Direct/snapshot damage also consumes explicit target-side runtime combat state
    when authoritative evidence supplies it; target identity windows are not treated
    as target debuff state. Non-cast periodic activation anchors consume an
    authoritative runtime anchor resolver from the stabilized snapshot when one is
    available; otherwise the periodic projection remains fail-closed.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        static_context_service: RotationStaticBuildContextService | None = None,
        weapon_attack_provider_factory: (
            RotationGenerateDDWeaponAttackProviderFactory | None
        ) = None,
        periodic_runtime_semantics_registry: (
            RotationDDPeriodicRuntimeSemanticsRegistryService | None
        ) = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.static_context_service = (
            static_context_service or RotationStaticBuildContextService()
        )
        self.weapon_attack_provider_factory = weapon_attack_provider_factory
        self.periodic_runtime_semantics_registry = (
            periodic_runtime_semantics_registry
            or RotationDDPeriodicRuntimeSemanticsRegistryService()
        )

    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence:
        role_key = _canonical_role(getattr(player_build, "Role", ""))
        if role_key not in _DD_ROLE_KEYS:
            raise ValueError(
                "automatic DD role evidence requires an explicit damage-dealer saved-build role"
            )
        if evidence_bundle.target_resistance is None:
            raise ValueError(
                "automatic DD role evidence requires explicit target resistance"
            )

        static_context = self.static_context_service.resolve(player_build)
        if not static_context.resolved:
            detail = "; ".join(static_context.unresolved) or "static build context unavailable"
            raise ValueError("canonical DD static build evidence is unresolved: " + detail)

        periodic_runtime_semantics = self.periodic_runtime_semantics_registry.load()
        target_resistance = float(evidence_bundle.target_resistance)
        static_plan_evidence = self._build_plan_evidence_provider(
            player_build=player_build,
            evidence_bundle=evidence_bundle,
            static_context=static_context,
            target_resistance=target_resistance,
            periodic_runtime_semantics=periodic_runtime_semantics,
            runtime_build_context_resolver=None,
            runtime_target_combat_state_resolver=None,
            activation_anchor_resolver=None,
        )
        runtime_context_service = RotationPlanRuntimeBuildContextService(
            static_context_service=self.static_context_service,
        )

        def runtime_provider_factory(snapshot):
            def resolve_runtime_context(
                time_seconds: float,
                sequence: int | None = None,
            ):
                result = runtime_context_service.resolve(
                    player_build,
                    runtime_combat_state_resolver=snapshot.runtime_combat_state_resolver,
                    time_seconds=time_seconds,
                    sequence=sequence,
                )
                if not result.resolved or result.context is None:
                    return result
                context = replace(
                    result.context,
                    target_resistance=target_resistance,
                    fight_duration=float(snapshot.plan.duration_seconds),
                )
                return replace(result, context=context)

            return self._build_plan_evidence_provider(
                player_build=player_build,
                evidence_bundle=evidence_bundle,
                static_context=static_context,
                target_resistance=target_resistance,
                periodic_runtime_semantics=periodic_runtime_semantics,
                runtime_build_context_resolver=(
                    resolve_runtime_context
                    if snapshot.runtime_combat_state_resolver is not None
                    else None
                ),
                runtime_target_combat_state_resolver=getattr(
                    snapshot,
                    "runtime_target_combat_state_resolver",
                    None,
                ),
                activation_anchor_resolver=getattr(
                    snapshot,
                    "runtime_activation_anchor_resolver",
                    None,
                ),
            )

        plan_evidence = _RotationGenerateSnapshotAwarePlanEvidenceProvider(
            static_provider=static_plan_evidence,
            runtime_provider_factory=runtime_provider_factory,
        )
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=plan_evidence,
            role_output_label="projected DPS",
            assigned_support_label="assigned support coverage",
            content_type=str(evidence_bundle.content_type or "").strip(),
            role_key=role_key,
        )

    def _build_plan_evidence_provider(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
        static_context,
        target_resistance: float,
        periodic_runtime_semantics: tuple[
            RotationPeriodicDamageRuntimeSemantics, ...
        ],
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None,
        runtime_target_combat_state_resolver: RotationRuntimeTargetCombatStateResolver | None,
        activation_anchor_resolver: PeriodicDamageActivationAnchorResolver | None,
    ):
        skill_provider = _RotationGenerateBarAwareSkillDamageProvider(
            database_path=self.database_path,
            static_context=static_context,
            target_resistance=target_resistance,
            periodic_runtime_semantics=periodic_runtime_semantics,
            runtime_build_context_resolver=runtime_build_context_resolver,
            runtime_target_combat_state_resolver=runtime_target_combat_state_resolver,
            activation_anchor_resolver=activation_anchor_resolver,
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


__all__ = [
    "RotationGenerateDDCanonicalWeaponAttackProviderFactory",
    "RotationGenerateDDRoleEvidenceSupport",
    "RotationGenerateDDWeaponAttackProviderFactory",
    "RotationRuntimeTargetCombatStateResolver",
]
