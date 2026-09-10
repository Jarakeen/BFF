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
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.skill_component_repository import SkillComponentRepository
from minmax.skill_tooltip_calculator import SkillTooltipCalculator
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationCandidatePeriodicDamageRuntimeProjectionService,
    RotationPeriodicDamageRuntimeSemantics,
)


class RotationCandidateSkillDamageEvidenceService:
    """Resolve scheduled skill damage through existing canonical combat math.

    This service is composition only. Canonical lower-snake-case skill identity and
    coefficient resolution remain owned by ``SkillCoefficientRepository`` and
    ``SkillTooltipCalculator``. Component identity remains owned by
    ``SkillComponentRepository``. DD stat caps, Damage Done, mitigation, critical
    handling, and Damage Taken remain owned by their existing combat services.

    Direct and periodic components deliberately share the same combat-routing
    helper. Periodic components differ only in *when* their already-resolved
    coefficient consequence occurs: the Phase 7 runtime projection proves the
    actual tick events for the exact parent cast, including recast and horizon
    clipping. Missing periodic runtime evidence remains unresolved rather than
    turning a full DoT tooltip value into cast-time damage.
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
        periodic_runtime_projection_service: (
            RotationCandidatePeriodicDamageRuntimeProjectionService | None
        ) = None,
        periodic_runtime_semantics: (
            tuple[RotationPeriodicDamageRuntimeSemantics, ...]
        ) = (),
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
        self.periodic_runtime_projection_service = periodic_runtime_projection_service
        self.periodic_runtime_semantics = tuple(periodic_runtime_semantics)

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

            component_damage = self._resolve_component_damage(
                base_value=float(component.final_value),
                classification=classification,
                dd_stats=dd_stats,
                damage_done=damage_done,
                damage_taken=damage_taken,
            )

            if classification.is_dot:
                if self.periodic_runtime_projection_service is None:
                    unresolved.append(
                        f"{action.name}: coefficient {component.coefficient_number} periodic damage requires horizon-aware runtime tick projection"
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

                # The coefficient's final value is the consequence for one
                # periodic occurrence. Runtime projection owns how many such
                # occurrences actually exist inside this exact cast instance.
                total_damage += component_damage * len(runtime_entry.events)
                continue

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

    def _resolve_component_damage(
        self,
        *,
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
