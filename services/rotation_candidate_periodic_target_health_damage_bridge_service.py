from __future__ import annotations

"""Bridge reviewed periodic target-Health timing into canonical DD tick damage.

This is intentionally narrow. It handles a skill action only when exactly one damage
component exists, that component is periodic, owns target-Health consequences, and
reviewed periodic runtime semantics exist. Mixed damage shapes that contain a reviewed
periodic target-Health component fail closed with an explicit diagnostic rather than
falling back as though target-Health review had never matched.

Source magnitude timing and target-Health timing remain separate reviewed facts.
``snapshot_at_cast`` reuses the base evaluator's cast-state magnitude path;
``dynamic_at_tick`` delegates each included occurrence back through the base
service's exact-time dynamic periodic resolver. This bridge owns no damage formula.
"""

from minmax.build_candidate_damage import calculation_result_from_build_context
from minmax.combat_damage_modifiers import damage_taken_from_target_state
from minmax.dd_stat_evaluation import evaluate_dd_stats
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_condition import SkillComponentConditionType
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageMagnitudePolicy,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_periodic_target_health_eligibility_service import (
    RotationPeriodicTargetHealthEligibilityService,
)


class RotationCandidatePeriodicTargetHealthDamageBridgeService:
    """Resolve reviewed periodic execute damage without duplicating canonical math."""

    def __init__(
        self,
        *,
        base: RotationCandidateSkillDamageEvidenceService,
        target_health_eligibility: RotationPeriodicTargetHealthEligibilityService,
        snapshot_resolver,
        target_identity: str,
    ) -> None:
        self.base = base
        self.target_health_eligibility = target_health_eligibility
        self.snapshot_resolver = snapshot_resolver
        self.target_identity = str(target_identity or "").strip()

    def evaluate_if_supported(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence | None:
        if action.kind is not RotationActionKind.SKILL or not action.name:
            return None

        calculation = calculation_result_from_build_context(self.base.context)
        if calculation is None:
            return None

        tooltip = self.base.calculator.evaluate_entity_id(action.name, self.base.context)
        if tooltip.skill is None or tooltip.unresolved:
            return None

        classifications = {
            row.coefficient_number: row
            for row in self.base.components.get_for_skill_rank(tooltip.skill.skill_rank_id)
        }
        damage_components = []
        periodic_target_health_components = []
        for component in tooltip.components:
            classification = classifications.get(component.coefficient_number)
            if classification is None or classification.effect_kind is not SkillEffectKind.DAMAGE:
                continue
            damage_components.append((component, classification))
            if not classification.is_dot:
                continue
            consequences = tuple(
                self.base.conditional_consequences.resolve(
                    tooltip.skill.skill_rank_id,
                    component.coefficient_number,
                )
            )
            target_health_consequences = tuple(
                consequence
                for consequence in consequences
                if consequence.condition.condition_type
                is SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT
            )
            if target_health_consequences:
                periodic_target_health_components.append(
                    (component, classification, target_health_consequences)
                )

        if not periodic_target_health_components:
            return None
        if len(periodic_target_health_components) != 1:
            numbers = ", ".join(
                str(component.coefficient_number)
                for component, _, _ in periodic_target_health_components
            )
            return self._unresolved(
                action,
                f"{action.name}: periodic target-Health bridge found multiple reviewed conditional damage components ({numbers}); component-level mixed-damage composition is required",
            )
        if len(damage_components) != 1:
            component = periodic_target_health_components[0][0]
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} periodic target-Health damage is part of a mixed {len(damage_components)}-component damage skill; component-level mixed-damage composition is required",
            )

        component, classification, target_health_consequences = (
            periodic_target_health_components[0]
        )
        if not classification.is_complete_damage_identity:
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} periodic target-Health damage classification is incomplete",
            )

        if self.base.periodic_runtime_projection_service is None:
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} periodic target-Health damage requires horizon-aware runtime tick projection",
            )

        semantic = self.base._periodic_semantics_for(
            action_name=action.name,
            coefficient_number=component.coefficient_number,
        )
        if semantic is None:
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} reviewed periodic runtime semantics are unavailable",
            )
        if semantic.magnitude_policy not in {
            PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST,
            PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK,
        }:
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} periodic target-Health bridge requires a reviewed source-magnitude timing policy",
            )

        projection = self.base.periodic_runtime_projection_service.project(
            plan=candidate.plan,
            semantics=self.base.periodic_runtime_semantics,
        )
        matching = tuple(
            entry
            for entry in projection.entries
            if entry.action.time_seconds == action.time_seconds
            and entry.action.sequence == action.sequence
            and entry.coefficient_number == component.coefficient_number
        )
        if len(matching) != 1:
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} periodic runtime projection expected one exact parent-cast match, found {len(matching)}",
            )
        runtime_entry = matching[0]
        if runtime_entry.unresolved:
            return self._unresolved(action, *runtime_entry.unresolved)

        eligibility = self.target_health_eligibility.evaluate(
            skill_name=action.name,
            coefficient_number=component.coefficient_number,
            consequences=target_health_consequences,
            runtime_events=runtime_entry.events,
            cast_time_seconds=float(action.time_seconds),
            cast_sequence=int(action.sequence),
            snapshot_resolver=self.snapshot_resolver,
            target_identity=self.target_identity,
        )
        if not eligibility.resolved:
            return self._unresolved(action, *eligibility.unresolved)
        if len(eligibility.occurrences) != len(runtime_entry.events):
            return self._unresolved(
                action,
                f"{action.name}: coefficient {component.coefficient_number} periodic target-Health eligibility expected {len(runtime_entry.events)} occurrences, found {len(eligibility.occurrences)}",
            )

        evaluation_context = EvaluationContext(
            fight_duration=self.base.context.fight_duration,
            target_resistance=self.base.context.target_resistance,
        )
        dd_stats = evaluate_dd_stats(calculation, evaluation_context)
        total_damage = 0.0

        for occurrence_index, (event, occurrence) in enumerate(
            zip(runtime_entry.events, eligibility.occurrences)
        ):
            if abs(float(event.time_seconds) - float(occurrence.time_seconds)) > 1e-9:
                return self._unresolved(
                    action,
                    f"{action.name}: coefficient {component.coefficient_number} periodic target-Health occurrence timing does not match runtime projection",
                )
            if not occurrence.include:
                continue

            if semantic.magnitude_policy is PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK:
                tick_damage, tick_unresolved = self.base._resolve_dynamic_periodic_damage(
                    action=action,
                    coefficient_number=component.coefficient_number,
                    classification=classification,
                    runtime_events=(event,),
                    semantic=semantic,
                )
                if tick_unresolved:
                    return self._unresolved(action, *tick_unresolved)
            else:
                tick_target_state = self.base._target_state_for_runtime_event(event)
                if (
                    self.base._requires_exploiter_target_state(self.base.context)
                    and tick_target_state is None
                ):
                    return self._unresolved(
                        action,
                        f"{action.name}: coefficient {component.coefficient_number} tick at {float(event.time_seconds):g}s: Exploiter requires authoritative target CombatState",
                    )

                tick_context = self.base._context_for_runtime_event(self.base.context, event)
                tick_damage = self.base._resolve_component_damage(
                    context=tick_context,
                    base_value=float(component.final_value),
                    classification=classification,
                    dd_stats=dd_stats,
                    damage_done=self.base._damage_done_for_context(
                        self.base.context,
                        tick_target_state,
                    ),
                    damage_taken=damage_taken_from_target_state(tick_target_state),
                )

            tick_damage *= self.base._occurrence_multiplier(semantic, occurrence_index)
            tick_damage *= float(occurrence.damage_multiplier)
            total_damage += tick_damage

        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=total_damage,
        )

    @staticmethod
    def _unresolved(action: RotationAction, *messages: str) -> RotationActionDamageEvidence:
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


__all__ = ["RotationCandidatePeriodicTargetHealthDamageBridgeService"]
