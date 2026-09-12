from __future__ import annotations

from pathlib import Path

from minmax.build_calculation_context import BuildCalculationContext
from minmax.build_candidate_damage import calculation_result_from_build_context
from minmax.combat_damage_modifiers import (
    damage_done_from_combat_state,
    damage_taken_from_target_state,
)
from minmax.combat_state import CombatState
from minmax.dd_damage import DDDamageEvent, calculate_dd_damage
from minmax.dd_mitigation import calculate_dd_mitigation
from minmax.dd_stat_evaluation import evaluate_dd_stats
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_tooltip_calculator import SkillTooltipCalculator
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageMagnitudePolicy,
    RotationCandidatePeriodicDamageRuntimeProjectionService,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_dd_reviewed_skill_component_repository import (
    RotationDDReviewedSkillComponentRepository,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationRuntimeBuildContextResolver,
)


class RotationCandidateSkillDamageEvidenceService:
    """Resolve scheduled skill damage through existing canonical combat math.

    This service is composition only. Canonical lower-snake-case skill identity and
    coefficient resolution remain owned by ``SkillCoefficientRepository`` and
    ``SkillTooltipCalculator``. Component identity remains owned by the reviewed DD
    overlay on top of ``SkillComponentRepository``. DD stat caps, Damage Done,
    mitigation, critical handling, and Damage Taken remain owned by their existing
    combat services.

    Direct and periodic components share the same combat-routing helper only when
    reviewed runtime evidence permits it. Periodic tick scheduling is owned by the
    shared runtime projection. Cast-time magnitude may be reused for all projected
    ticks only when reviewed semantics explicitly say ``snapshot_at_cast``. Dynamic
    per-tick magnitude is recomputed only when an authoritative exact-time runtime
    build-context resolver is supplied for every projected tick. Explicit
    successive-hit scaling is applied by occurrence index only when reviewed
    semantics provide a multiplier.
    """

    def __init__(
        self,
        *,
        database_path: str | Path,
        context: BuildCalculationContext,
        calculator: SkillTooltipCalculator | None = None,
        component_repository: SkillComponentRepository | object | None = None,
        target_combat_state: CombatState | None = None,
        target_critical_resistance: float = 0.0,
        periodic_runtime_projection_service: (
            RotationCandidatePeriodicDamageRuntimeProjectionService | None
        ) = None,
        periodic_runtime_semantics: (
            tuple[RotationPeriodicDamageRuntimeSemantics, ...]
        ) = (),
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.context = context
        repository = SkillCoefficientRepository(self.database_path)
        self.calculator = calculator or SkillTooltipCalculator(repository)
        self.components = component_repository or RotationDDReviewedSkillComponentRepository(
            self.database_path
        )
        self.target_combat_state = target_combat_state
        self.target_critical_resistance = float(target_critical_resistance)
        self.periodic_runtime_projection_service = periodic_runtime_projection_service
        self.periodic_runtime_semantics = tuple(periodic_runtime_semantics)
        self.runtime_build_context_resolver = runtime_build_context_resolver

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.SKILL:
            return self._unresolved(
                action,
                f"{action.kind.value} damage requires its dedicated canonical action evaluator",
            )
        if not action.name:
            return self._unresolved(
                action,
                "scheduled skill action has no canonical skill identity",
            )

        calculation = calculation_result_from_build_context(self.context)
        if calculation is None:
            return self._unresolved(
                action,
                "canonical static context has no resolved core stat state",
            )

        tooltip = self.calculator.evaluate_entity_id(action.name, self.context)
        if tooltip.skill is None:
            messages = tooltip.unresolved or (
                f"canonical skill identity {action.name!r} did not resolve to a skill rank",
            )
            return self._unresolved(action, *messages)
        if tooltip.unresolved:
            return self._unresolved(action, *tooltip.unresolved)

        classifications = {
            item.coefficient_number: item
            for item in self.components.get_for_skill_rank(tooltip.skill.skill_rank_id)
        }
        evaluation_context = EvaluationContext(
            fight_duration=self.context.fight_duration,
            target_resistance=self.context.target_resistance,
        )
        dd_stats = evaluate_dd_stats(calculation, evaluation_context)
        damage_done = damage_done_from_combat_state(self.context.combat_state)
        damage_taken = damage_taken_from_target_state(self.target_combat_state)

        periodic_projection = None
        unresolved: list[str] = []
        total_damage = 0.0
        saw_damage_component = False

        for component in tooltip.components:
            classification = classifications.get(component.coefficient_number)
            if classification is None:
                unresolved.append(
                    f"{action.name}: coefficient {component.coefficient_number} component classification unavailable"
                )
                continue
            if classification.effect_kind is SkillEffectKind.UNKNOWN:
                unresolved.append(
                    f"{action.name}: coefficient {component.coefficient_number} effect kind unresolved"
                )
                continue
            if classification.effect_kind is not SkillEffectKind.DAMAGE:
                continue

            saw_damage_component = True
            if not classification.is_complete_damage_identity:
                unresolved.append(
                    f"{action.name}: coefficient {component.coefficient_number} damage classification incomplete"
                )
                continue

            if classification.is_dot:
                if self.periodic_runtime_projection_service is None:
                    unresolved.append(
                        f"{action.name}: coefficient {component.coefficient_number} periodic damage requires horizon-aware runtime tick projection"
                    )
                    continue

                semantic = self._periodic_semantics_for(
                    action_name=action.name,
                    coefficient_number=component.coefficient_number,
                )
                if semantic is None:
                    unresolved.append(
                        f"{action.name}: coefficient {component.coefficient_number} reviewed periodic runtime semantics are unavailable"
                    )
                    continue
                if semantic.magnitude_policy is None:
                    unresolved.append(
                        f"{action.name}: coefficient {component.coefficient_number} periodic magnitude timing policy is unavailable"
                    )
                    continue

                if periodic_projection is None:
                    periodic_projection = self.periodic_runtime_projection_service.project(
                        plan=candidate.plan,
                        semantics=self.periodic_runtime_semantics,
                    )

                matching = tuple(
                    entry
                    for entry in periodic_projection.entries
                    if entry.action.time_seconds == action.time_seconds
                    and entry.action.sequence == action.sequence
                    and entry.coefficient_number == component.coefficient_number
                )
                if len(matching) != 1:
                    unresolved.append(
                        f"{action.name}: coefficient {component.coefficient_number} periodic runtime projection expected one exact parent-cast match, found {len(matching)}"
                    )
                    continue
                runtime_entry = matching[0]
                if runtime_entry.unresolved:
                    unresolved.extend(runtime_entry.unresolved)
                    continue

                if semantic.magnitude_policy is PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK:
                    dynamic_damage, dynamic_unresolved = self._resolve_dynamic_periodic_damage(
                        action=action,
                        coefficient_number=component.coefficient_number,
                        classification=classification,
                        runtime_events=runtime_entry.events,
                        semantic=semantic,
                    )
                    if dynamic_unresolved:
                        unresolved.extend(dynamic_unresolved)
                        continue
                    total_damage += dynamic_damage
                    continue

                component_damage = self._resolve_component_damage(
                    context=self.context,
                    base_value=float(component.final_value),
                    classification=classification,
                    dd_stats=dd_stats,
                    damage_done=damage_done,
                    damage_taken=damage_taken,
                )
                # Explicit SNAPSHOT_AT_CAST evidence permits one cast-time damage
                # consequence to be reused for each projected periodic occurrence.
                total_damage += sum(
                    component_damage
                    * self._occurrence_multiplier(semantic, occurrence_index)
                    for occurrence_index, _event in enumerate(runtime_entry.events)
                )
                continue

            component_damage = self._resolve_component_damage(
                context=self.context,
                base_value=float(component.final_value),
                classification=classification,
                dd_stats=dd_stats,
                damage_done=damage_done,
                damage_taken=damage_taken,
            )
            total_damage += component_damage

        if unresolved:
            return self._unresolved(action, *unresolved)

        # A fully classified utility/healing skill legitimately contributes zero
        # damage. Unknown component identity was already rejected above.
        if not saw_damage_component:
            total_damage = 0.0

        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=total_damage,
        )

    def _resolve_dynamic_periodic_damage(
        self,
        *,
        action: RotationAction,
        coefficient_number: int,
        classification: SkillComponentClassification,
        runtime_events,
        semantic: RotationPeriodicDamageRuntimeSemantics,
    ) -> tuple[float, tuple[str, ...]]:
        if self.runtime_build_context_resolver is None:
            return 0.0, (
                f"{action.name}: coefficient {coefficient_number} dynamic per-tick magnitude requires exact-time runtime build context projection",
            )

        total_damage = 0.0
        unresolved: list[str] = []
        damage_taken = damage_taken_from_target_state(self.target_combat_state)

        for occurrence_index, event in enumerate(runtime_events):
            # Runtime ticks are not plan actions. Sequence=None asks the canonical
            # runtime/bar projector for the state after all plan actions at this
            # exact timestamp rather than fabricating an ordering token for the tick.
            runtime = self.runtime_build_context_resolver(
                float(event.time_seconds),
                None,
            )
            if not runtime.resolved or runtime.context is None:
                detail = tuple(runtime.unresolved) or (
                    "exact-time runtime build context is unresolved",
                )
                unresolved.extend(
                    f"{action.name}: coefficient {coefficient_number} tick at {float(event.time_seconds):g}s: {message}"
                    for message in detail
                )
                continue

            tick_context = runtime.context
            calculation = calculation_result_from_build_context(tick_context)
            if calculation is None:
                unresolved.append(
                    f"{action.name}: coefficient {coefficient_number} tick at {float(event.time_seconds):g}s has no resolved canonical core stat state"
                )
                continue

            tick_tooltip = self.calculator.evaluate_entity_id(action.name, tick_context)
            if tick_tooltip.skill is None or tick_tooltip.unresolved:
                detail = tick_tooltip.unresolved or (
                    "canonical skill rank is unavailable at runtime tick",
                )
                unresolved.extend(
                    f"{action.name}: coefficient {coefficient_number} tick at {float(event.time_seconds):g}s: {message}"
                    for message in detail
                )
                continue

            tick_components = tuple(
                item
                for item in tick_tooltip.components
                if item.coefficient_number == coefficient_number
            )
            if len(tick_components) != 1:
                unresolved.append(
                    f"{action.name}: coefficient {coefficient_number} tick at {float(event.time_seconds):g}s expected one runtime tooltip component, found {len(tick_components)}"
                )
                continue

            evaluation_context = EvaluationContext(
                fight_duration=tick_context.fight_duration,
                target_resistance=tick_context.target_resistance,
            )
            tick_dd_stats = evaluate_dd_stats(calculation, evaluation_context)
            tick_damage_done = damage_done_from_combat_state(tick_context.combat_state)
            total_damage += self._resolve_component_damage(
                context=tick_context,
                base_value=float(tick_components[0].final_value),
                classification=classification,
                dd_stats=tick_dd_stats,
                damage_done=tick_damage_done,
                damage_taken=damage_taken,
            ) * self._occurrence_multiplier(semantic, occurrence_index)

        return total_damage, tuple(dict.fromkeys(unresolved))

    @staticmethod
    def _occurrence_multiplier(
        semantic: RotationPeriodicDamageRuntimeSemantics,
        occurrence_index: int,
    ) -> float:
        multiplier = semantic.successive_hit_multiplier
        if multiplier is None:
            return 1.0
        return float(multiplier) ** int(occurrence_index)

    def _periodic_semantics_for(
        self,
        *,
        action_name: str,
        coefficient_number: int,
    ) -> RotationPeriodicDamageRuntimeSemantics | None:
        identity = ability_entity_id(action_name)
        matches = tuple(
            semantic
            for semantic in self.periodic_runtime_semantics
            if semantic.skill_entity_id == identity
            and semantic.coefficient_number == coefficient_number
        )
        return matches[0] if len(matches) == 1 else None

    def _resolve_component_damage(
        self,
        *,
        context: BuildCalculationContext,
        base_value: float,
        classification: SkillComponentClassification,
        dd_stats,
        damage_done,
        damage_taken,
    ) -> float:
        """Route one already-resolved coefficient value through canonical DD math."""

        event = DDDamageEvent(
            base_value=float(base_value),
            scaling_coefficient=0.0,
            damage_type=classification.damage_type,
            can_crit=bool(classification.can_crit),
            is_dot=bool(classification.is_dot),
            is_aoe=bool(classification.is_aoe),
        )
        raw = calculate_dd_damage(
            event,
            dd_stats,
            damage_done=damage_done,
            damage_taken=damage_taken,
            target_critical_resistance=self.target_critical_resistance,
        )
        mitigation = None
        if context.target_resistance is not None and raw.penetration_stat is not None:
            mitigation = calculate_dd_mitigation(
                target_resistance=context.target_resistance,
                penetration=raw.penetration,
            )
        resolved = calculate_dd_damage(
            event,
            dd_stats,
            mitigation=mitigation,
            damage_done=damage_done,
            damage_taken=damage_taken,
            target_critical_resistance=self.target_critical_resistance,
        )
        return float(resolved.final_damage)

    @staticmethod
    def _unresolved(
        action: RotationAction,
        *messages: str,
    ) -> RotationActionDamageEvidence:
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in messages
                    if str(message).strip()
                )
            ),
        )


__all__ = ["RotationCandidateSkillDamageEvidenceService"]
