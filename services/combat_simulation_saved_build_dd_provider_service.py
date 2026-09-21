from __future__ import annotations

"""Compose canonical saved-build DD action damage for Combat Simulation.

This module is simulation composition only. It owns no ESO damage formulas. Skill,
Light Attack, Heavy Attack, Ultimate, periodic timing, static build state, target
mitigation, and execute semantics remain with their existing canonical services.
"""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from minmax.build_candidate_damage import calculation_result_from_build_context
from minmax.combat_state import CombatState
from minmax.combat_state_snapshot import CombatStateSnapshot
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_active_bar_context_resolver_service import (
    RotationActiveBarContextResolverService,
)
from services.rotation_candidate_action_damage_evidence_service import (
    RotationActionDamageProvider,
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationActionDamageOccurrenceEvidence,
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
from services.rotation_dd_output_context_relevance_service import (
    RotationDDOutputContextRelevanceService,
)
from services.rotation_dd_relevant_static_context_service import (
    RotationDDRelevantStaticContextService,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationRuntimeBuildContextResolver,
)
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationSavedBuildWeaponAttackEvaluationService,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextResolution,
    RotationStaticBuildContextService,
)


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}

TargetCombatStateResolver = Callable[[float, int | None], CombatState]
TargetResistanceResolver = Callable[[float, int | None], float]
TargetSnapshotResolver = Callable[[float, int | None], CombatStateSnapshot | None]


@dataclass(frozen=True)
class CombatSimulationSavedBuildDDProviderResolution:
    provider: RotationActionDamageProvider | None
    static_context: RotationStaticBuildContextResolution | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.provider is not None and not self.unresolved


class _SimulationTemporalSkillProvider:
    """Prevent whole-horizon periodic totals from masquerading as cast-time damage.

    Rotation role-output evidence correctly aggregates periodic ticks under their
    parent cast. Combat Simulation needs occurrence timestamps instead. Until the
    occurrence-level bridge is supplied, any skill/Ultimate with a reviewed periodic
    damage component fails closed rather than front-loading its total damage.
    """

    def __init__(
        self,
        *,
        delegate: RotationActionDamageProvider,
        timing_service: RotationCandidatePeriodicDamageTimingEvidenceService,
    ) -> None:
        self.delegate = delegate
        self.timing_service = timing_service

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
            report = self.timing_service.inspect_action(action)
            if report.entries:
                return RotationActionDamageEvidence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=None,
                    unresolved=(
                        f"{action.name}: periodic damage has canonical whole-plan magnitude "
                        "but requires occurrence-level tick damage before Combat Simulation "
                        "may apply it to target Health",
                    ),
                )
        return self.delegate.evaluate_action(candidate=candidate, action=action)

    def evaluate_action_occurrences(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageOccurrenceEvidence:
        if hasattr(self.delegate, "evaluate_action_occurrences"):
            return self.delegate.evaluate_action_occurrences(
                candidate=candidate,
                action=action,
            )
        evidence = self.evaluate_action(candidate=candidate, action=action)
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=action.time_seconds,
            action_sequence=action.sequence,
            unresolved=evidence.unresolved
            or (
                f"{action.name or action.kind.value}: exact-time damage occurrences are unavailable",
            ),
        )


class _UnresolvedDamageProvider:
    def __init__(self, unresolved: tuple[str, ...]) -> None:
        self.unresolved = tuple(
            dict.fromkeys(
                str(message).strip()
                for message in unresolved
                if str(message).strip()
            )
        ) or ("canonical damage evidence is unresolved",)

    def evaluate_action(self, *, candidate, action) -> RotationActionDamageEvidence:
        del candidate
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=self.unresolved,
        )


class _StaticBarAwareSkillProvider:
    def __init__(
        self,
        *,
        database_path: Path,
        static_context: RotationStaticBuildContextResolution,
        plan: RotationPlan,
        target_resistance: float,
        target_combat_state_resolver: TargetCombatStateResolver | None,
        target_resistance_resolver: TargetResistanceResolver | None,
        target_snapshot_resolver: TargetSnapshotResolver | None,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None,
        activation_anchor_resolver: PeriodicDamageActivationAnchorResolver | None,
        execute_target_identity: str,
        initial_bar: str,
    ) -> None:
        self.database_path = database_path
        self.static_context = static_context
        self.plan = plan
        self.target_resistance = float(target_resistance)
        self.target_combat_state_resolver = target_combat_state_resolver
        self.target_resistance_resolver = target_resistance_resolver
        self.target_snapshot_resolver = target_snapshot_resolver
        self.runtime_build_context_resolver = runtime_build_context_resolver
        self.activation_anchor_resolver = activation_anchor_resolver
        self.execute_target_identity = str(execute_target_identity or "").strip()
        self.initial_bar = str(initial_bar or "").strip().casefold()
        self.semantics = RotationDDPeriodicRuntimeSemanticsRegistryService().load()
        self.periodic_projection = (
            RotationCandidatePeriodicDamageRuntimeProjectionService(
                RotationCandidatePeriodicDamageTimingEvidenceService(database_path),
                activation_anchor_resolver=activation_anchor_resolver,
            )
            if self.semantics
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
            resolver = RotationActiveBarContextResolverService(
                static_context=self.static_context,
                plan=candidate.plan,
                initial_bar=self.initial_bar,
            )
            context = resolver.context_at(action.time_seconds, action.sequence)
        target_resistance = (
            float(self.target_resistance_resolver(action.time_seconds, action.sequence))
            if self.target_resistance_resolver is not None
            else self.target_resistance
        )
        context = replace(
            context,
            target_resistance=target_resistance,
            fight_duration=float(candidate.plan.duration_seconds),
        )
        target_state = (
            self.target_combat_state_resolver(action.time_seconds, action.sequence)
            if self.target_combat_state_resolver is not None
            else None
        )
        return RotationCandidateSkillDamageEvidenceService(
            database_path=self.database_path,
            context=context,
            target_combat_state=target_state,
            periodic_runtime_projection_service=self.periodic_projection,
            periodic_runtime_semantics=self.semantics,
            runtime_build_context_resolver=self.runtime_build_context_resolver,
            runtime_target_combat_state_resolver=self.target_combat_state_resolver,
            runtime_target_resistance_resolver=self.target_resistance_resolver,
            runtime_target_snapshot_resolver=self.target_snapshot_resolver,
            execute_target_identity=self.execute_target_identity,
        ).evaluate_action(
            candidate=candidate,
            action=action,
        )


    def evaluate_action_occurrences(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageOccurrenceEvidence:
        if action.kind is not RotationActionKind.SKILL:
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=action.time_seconds,
                action_sequence=action.sequence,
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
                return RotationActionDamageOccurrenceEvidence(
                    action_time_seconds=action.time_seconds,
                    action_sequence=action.sequence,
                    unresolved=unresolved,
                )
            context = runtime.context
        else:
            resolver = RotationActiveBarContextResolverService(
                static_context=self.static_context,
                plan=candidate.plan,
                initial_bar=self.initial_bar,
            )
            context = resolver.context_at(action.time_seconds, action.sequence)
        target_resistance = (
            float(self.target_resistance_resolver(action.time_seconds, action.sequence))
            if self.target_resistance_resolver is not None
            else self.target_resistance
        )
        context = replace(
            context,
            target_resistance=target_resistance,
            fight_duration=float(candidate.plan.duration_seconds),
        )
        target_state = (
            self.target_combat_state_resolver(action.time_seconds, action.sequence)
            if self.target_combat_state_resolver is not None
            else None
        )
        return RotationCandidateSkillDamageEvidenceService(
            database_path=self.database_path,
            context=context,
            target_combat_state=target_state,
            periodic_runtime_projection_service=self.periodic_projection,
            periodic_runtime_semantics=self.semantics,
            runtime_build_context_resolver=self.runtime_build_context_resolver,
            runtime_target_combat_state_resolver=self.target_combat_state_resolver,
            runtime_target_resistance_resolver=self.target_resistance_resolver,
            runtime_target_snapshot_resolver=self.target_snapshot_resolver,
            execute_target_identity=self.execute_target_identity,
        ).evaluate_action_occurrences(
            candidate=candidate,
            action=action,
        )


class _StaticBarAwareLightAttackProvider:
    def __init__(
        self,
        *,
        weapon_resolution,
        static_context: RotationStaticBuildContextResolution,
        target_resistance: float,
        target_combat_state_resolver: TargetCombatStateResolver | None,
        target_resistance_resolver: TargetResistanceResolver | None,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None,
        initial_bar: str,
    ) -> None:
        self.weapon_resolution = weapon_resolution
        self.static_context = static_context
        self.target_resistance = float(target_resistance)
        self.target_combat_state_resolver = target_combat_state_resolver
        self.target_resistance_resolver = target_resistance_resolver
        self.runtime_build_context_resolver = runtime_build_context_resolver
        self.initial_bar = str(initial_bar or "").strip().casefold()

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if self.runtime_build_context_resolver is not None:
            runtime = self.runtime_build_context_resolver(
                float(action.time_seconds),
                int(action.sequence),
            )
            if not runtime.resolved or runtime.context is None:
                return RotationActionDamageEvidence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=None,
                    unresolved=tuple(runtime.unresolved)
                    or ("runtime light-attack build context is unresolved",),
                )
            context = runtime.context
            active_bar = runtime.active_bar
        else:
            resolver = RotationActiveBarContextResolverService(
                static_context=self.static_context,
                plan=candidate.plan,
                initial_bar=self.initial_bar,
            )
            context = resolver.context_at(action.time_seconds, action.sequence)
            active_bar = context.active_bar
        evaluation = self.weapon_resolution.evaluation_for(active_bar)
        calculation = calculation_result_from_build_context(context)
        if evaluation is None or calculation is None:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{context.active_bar} canonical light-attack evaluation is unavailable",
                ),
            )
        evaluation = replace(evaluation, stats=calculation)
        target_state = (
            self.target_combat_state_resolver(action.time_seconds, action.sequence)
            if self.target_combat_state_resolver is not None
            else None
        )
        resistance = (
            float(self.target_resistance_resolver(action.time_seconds, action.sequence))
            if self.target_resistance_resolver is not None
            else self.target_resistance
        )
        return RotationCandidateLightAttackDamageEvidenceService(
            build=self.weapon_resolution.build,
            evaluation=evaluation,
            initial_bar=self.initial_bar,
            evaluation_context=EvaluationContext(
                fight_duration=float(candidate.plan.duration_seconds),
                target_resistance=resistance,
            ),
            attacker_combat_state=getattr(context, "combat_state", None),
            target_combat_state=target_state,
        ).evaluate_action(candidate=candidate, action=action)


class _StaticBarAwareHeavyAttackProvider:
    def __init__(
        self,
        *,
        weapon_resolution,
        static_context: RotationStaticBuildContextResolution,
        target_resistance: float,
        target_combat_state_resolver: TargetCombatStateResolver | None,
        target_resistance_resolver: TargetResistanceResolver | None,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None,
        initial_bar: str,
    ) -> None:
        self.weapon_resolution = weapon_resolution
        self.static_context = static_context
        self.target_resistance = float(target_resistance)
        self.target_combat_state_resolver = target_combat_state_resolver
        self.target_resistance_resolver = target_resistance_resolver
        self.runtime_build_context_resolver = runtime_build_context_resolver
        self.initial_bar = str(initial_bar or "").strip().casefold()

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        completion_evidence = (
            RotationHeavySustainProjectionService.completion_evidence_from_verified_reservations(
                candidate.plan
            )
        )
        completion = next(
            (
                item
                for item in completion_evidence
                if item.action_time_seconds == action.time_seconds
                and item.action_sequence == action.sequence
            ),
            None,
        )
        runtime_time = (
            float(completion.completion_time_seconds)
            if completion is not None
            else float(action.time_seconds)
        )
        runtime_sequence = None if completion is not None else int(action.sequence)
        if self.runtime_build_context_resolver is not None:
            runtime = self.runtime_build_context_resolver(
                runtime_time,
                runtime_sequence,
            )
            if not runtime.resolved or runtime.context is None:
                return RotationActionDamageEvidence(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    damage_value=None,
                    unresolved=tuple(runtime.unresolved)
                    or ("runtime heavy-attack build context is unresolved",),
                )
            context = runtime.context
            active_bar = runtime.active_bar
        else:
            resolver = RotationActiveBarContextResolverService(
                static_context=self.static_context,
                plan=candidate.plan,
                initial_bar=self.initial_bar,
            )
            context = resolver.context_at(action.time_seconds, action.sequence)
            active_bar = context.active_bar
        evaluation = self.weapon_resolution.evaluation_for(active_bar)
        calculation = calculation_result_from_build_context(context)
        if evaluation is None or calculation is None:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{context.active_bar} canonical heavy-attack evaluation is unavailable",
                ),
            )
        evaluation = replace(evaluation, stats=calculation)

        target_time = (
            float(completion.completion_time_seconds)
            if completion is not None
            else float(action.time_seconds)
        )
        target_sequence = None if completion is not None else int(action.sequence)
        target_state = (
            self.target_combat_state_resolver(target_time, target_sequence)
            if self.target_combat_state_resolver is not None
            else None
        )
        resistance = (
            float(self.target_resistance_resolver(target_time, target_sequence))
            if self.target_resistance_resolver is not None
            else self.target_resistance
        )
        return RotationCandidateHeavyAttackDamageEvidenceService(
            build=self.weapon_resolution.build,
            evaluation=evaluation,
            initial_bar=self.initial_bar,
            completion_evidence=completion_evidence,
            evaluation_context=EvaluationContext(
                fight_duration=float(candidate.plan.duration_seconds),
                target_resistance=resistance,
            ),
            attacker_combat_state=getattr(context, "combat_state", None),
            target_combat_state=target_state,
        ).evaluate_action(candidate=candidate, action=action)


class CombatSimulationSavedBuildDDProviderService:
    """Compose the canonical DD action provider for one saved build and plan."""

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        static_context_service: RotationStaticBuildContextService | None = None,
        weapon_evaluation_service: RotationSavedBuildWeaponAttackEvaluationService | None = None,
        relevance_service: RotationDDOutputContextRelevanceService | None = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        static_delegate = static_context_service or RotationStaticBuildContextService()
        self.static_context_service = RotationDDRelevantStaticContextService(
            static_delegate,
            relevance_service=(
                relevance_service or RotationDDOutputContextRelevanceService()
            ),
        )
        self.weapon_evaluation_service = (
            weapon_evaluation_service
            or RotationSavedBuildWeaponAttackEvaluationService(self.database_path)
        )

    def resolve(
        self,
        *,
        player_build: PlayerBuild,
        plan: RotationPlan,
        target_resistance: float,
        initial_bar: str = "front",
        target_combat_state_resolver: TargetCombatStateResolver | None = None,
        target_resistance_resolver: TargetResistanceResolver | None = None,
        target_snapshot_resolver: TargetSnapshotResolver | None = None,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
        activation_anchor_resolver: PeriodicDamageActivationAnchorResolver | None = None,
        execute_target_identity: str = "",
    ) -> CombatSimulationSavedBuildDDProviderResolution:
        role = " ".join(str(getattr(player_build, "Role", "") or "").strip().casefold().replace("_", " ").split())
        if role not in _DD_ROLE_KEYS:
            return CombatSimulationSavedBuildDDProviderResolution(
                provider=None,
                unresolved=(
                    "combat simulation canonical DD provider requires a saved damage-dealer build",
                ),
            )

        filtered = self.static_context_service.resolve(player_build)
        if not filtered.resolved:
            unresolved = tuple(filtered.unresolved)
            if not filtered.progression.resolved and not unresolved:
                unresolved = ("canonical DD character progression is unresolved",)
            if not filtered.contexts and not unresolved:
                unresolved = ("canonical DD static build contexts are unavailable",)
            return CombatSimulationSavedBuildDDProviderResolution(
                provider=None,
                static_context=filtered,
                unresolved=unresolved,
            )

        base_skill = _StaticBarAwareSkillProvider(
            database_path=self.database_path,
            static_context=filtered,
            plan=plan,
            target_resistance=float(target_resistance),
            target_combat_state_resolver=target_combat_state_resolver,
            target_resistance_resolver=target_resistance_resolver,
            target_snapshot_resolver=target_snapshot_resolver,
            runtime_build_context_resolver=runtime_build_context_resolver,
            activation_anchor_resolver=activation_anchor_resolver,
            execute_target_identity=execute_target_identity,
            initial_bar=initial_bar,
        )
        timing_service = RotationCandidatePeriodicDamageTimingEvidenceService(
            self.database_path
        )
        skill = _SimulationTemporalSkillProvider(
            delegate=base_skill,
            timing_service=timing_service,
        )
        ultimate = RotationCandidateUltimateDamageEvidenceService(
            skill_damage_delegate=skill,
        )

        weapon_resolution = self.weapon_evaluation_service.resolve(
            player_build=player_build,
            static_context=filtered,
        )
        if weapon_resolution.resolved:
            light: RotationActionDamageProvider | None = _StaticBarAwareLightAttackProvider(
                weapon_resolution=weapon_resolution,
                static_context=filtered,
                target_resistance=float(target_resistance),
                target_combat_state_resolver=target_combat_state_resolver,
                target_resistance_resolver=target_resistance_resolver,
                runtime_build_context_resolver=runtime_build_context_resolver,
                initial_bar=initial_bar,
            )
            heavy: RotationActionDamageProvider | None = _StaticBarAwareHeavyAttackProvider(
                weapon_resolution=weapon_resolution,
                static_context=filtered,
                target_resistance=float(target_resistance),
                target_combat_state_resolver=target_combat_state_resolver,
                target_resistance_resolver=target_resistance_resolver,
                runtime_build_context_resolver=runtime_build_context_resolver,
                initial_bar=initial_bar,
            )
        else:
            unresolved_weapon = _UnresolvedDamageProvider(weapon_resolution.unresolved)
            light = unresolved_weapon
            heavy = unresolved_weapon

        router = RotationCandidateActionDamageEvidenceService(
            skill_provider=skill,
            light_attack_provider=light,
            heavy_attack_provider=heavy,
            ultimate_provider=ultimate,
        )
        return CombatSimulationSavedBuildDDProviderResolution(
            provider=router,
            static_context=filtered,
            unresolved=(),
        )


__all__ = [
    "CombatSimulationSavedBuildDDProviderResolution",
    "CombatSimulationSavedBuildDDProviderService",
    "TargetCombatStateResolver",
    "TargetResistanceResolver",
    "TargetSnapshotResolver",
]
