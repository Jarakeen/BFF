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
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_tooltip_calculator import SkillTooltipCalculator
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class RotationCandidateSkillDamageEvidenceService:
    """Resolve direct scheduled skill damage through existing canonical combat math.

    This service is composition only. Canonical lower-snake-case skill identity and
    coefficient resolution remain owned by ``SkillCoefficientRepository`` and
    ``SkillTooltipCalculator``. Component identity remains owned by
    ``SkillComponentRepository``. DD stat caps, Damage Done, mitigation, critical
    handling, and Damage Taken remain owned by their existing combat services.

    Periodic damage is deliberately unresolved here. A cast-time action cannot claim
    the full value of a DoT without a horizon-aware tick projection that understands
    refreshes, expirations, target state, and encounter downtime.
    """

    def __init__(
        self,
        *,
        database_path: str | Path,
        context: BuildCalculationContext,
        calculator: SkillTooltipCalculator | None = None,
        component_repository: SkillComponentRepository | None = None,
        target_combat_state: CombatState | None = None,
        target_critical_resistance: float = 0.0,
    ) -> None:
        self.database_path = Path(database_path)
        self.context = context
        repository = SkillCoefficientRepository(self.database_path)
        self.calculator = calculator or SkillTooltipCalculator(repository)
        self.components = component_repository or SkillComponentRepository(
            self.database_path
        )
        self.target_combat_state = target_combat_state
        self.target_critical_resistance = float(target_critical_resistance)

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        del candidate  # Exact action identity is verified by the whole-plan aggregator.

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
                unresolved.append(
                    f"{action.name}: coefficient {component.coefficient_number} periodic damage requires horizon-aware runtime tick projection"
                )
                continue

            event = DDDamageEvent(
                base_value=float(component.final_value),
                scaling_coefficient=0.0,
                damage_type=classification.damage_type,
                can_crit=bool(classification.can_crit),
                is_dot=False,
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
            if (
                self.context.target_resistance is not None
                and raw.penetration_stat is not None
            ):
                mitigation = calculate_dd_mitigation(
                    target_resistance=self.context.target_resistance,
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
            total_damage += float(resolved.final_damage)

        if unresolved:
            return self._unresolved(action, *unresolved)

        # A fully classified utility/healing skill legitimately contributes zero
        # direct damage. Unknown component identity was already rejected above.
        if not saw_damage_component:
            total_damage = 0.0

        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=total_damage,
        )

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
                str(message).strip()
                for message in messages
                if str(message).strip()
            ),
        )


__all__ = ["RotationCandidateSkillDamageEvidenceService"]
