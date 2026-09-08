from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.build_calculation_context import BuildCalculationContext
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_tooltip_calculator import SkillTooltipResult
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeHealingEventResult:
    """One reviewed healing event from an actual saved-build context.

    ``normal_heal`` is the sum of HEAL-classified coefficient components after
    the canonical saved-build actual-effect pipeline has applied sheet Healing
    Done and verified component-scoped healing CP. ``critical_heal`` is the same
    event assuming that heal crits. It is deliberately not an expected-value
    model and therefore does not multiply by critical chance.
    """

    entity_id: str
    normal_heal: float | None
    critical_heal: float | None
    critical_healing_bonus: float | None
    critical_multiplier: float | None
    heal_coefficient_numbers: tuple[int, ...]
    tooltip_result: SkillTooltipResult
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return (
            self.normal_heal is not None
            and self.critical_heal is not None
            and self.critical_healing_bonus is not None
            and not self.unresolved
        )


class ExtremeHealingEventService:
    """Evaluate one real heal without collapsing healing stats into one number.

    BFF already owns coefficient scaling, component classification, saved-build
    Healing Done, and healing CP semantics. This service only composes those
    reviewed layers for the Extreme lab and adds the canonical 50% base critical
    healing multiplier from the UESP SpellCritHealing/WeaponCritHealing formula.

    Critical chance is intentionally absent. "Largest actual heal" asks how big
    the event can be when it crits; an expected-heal objective is a separate
    probability problem and must remain separate.
    """

    BASE_CRITICAL_HEALING = 0.50

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        tooltip_service: SavedBuildSkillTooltipService | None = None,
    ) -> None:
        self.database_path = Path(database_path or get_data_dir() / "eso.db")
        self.tooltip_service = tooltip_service or SavedBuildSkillTooltipService(
            self.database_path
        )

    def evaluate(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
        entity_id: str,
    ) -> ExtremeHealingEventResult:
        result = self.tooltip_service.evaluate_entity_id(
            build=build,
            context=context,
            entity_id=entity_id,
        )
        unresolved = list(result.unresolved)

        heal_numbers: tuple[int, ...] = ()
        if result.skill is None:
            unresolved.append(f"{entity_id}: skill rank is unresolved")
        else:
            heal_numbers = tuple(
                int(component.coefficient_number)
                for component in self.tooltip_service.components.get_for_skill_rank(
                    result.skill.skill_rank_id
                )
                if component.effect_kind is SkillEffectKind.HEAL
            )
            if not heal_numbers:
                unresolved.append(f"{entity_id}: no HEAL-classified coefficient components")

        actual_by_number = {
            int(trace.coefficient_number): float(trace.output_value)
            for trace in result.component_actual_effect_trace
        }
        base_by_number = {
            int(trace.coefficient_number): float(trace.final_value)
            for trace in result.components
        }

        normal_heal: float | None = None
        if heal_numbers:
            missing = [
                number
                for number in heal_numbers
                if number not in actual_by_number and number not in base_by_number
            ]
            if missing:
                unresolved.append(
                    f"{entity_id}: HEAL coefficient values unavailable: "
                    + ", ".join(str(number) for number in missing)
                )
            else:
                normal_heal = sum(
                    actual_by_number.get(number, base_by_number[number])
                    for number in heal_numbers
                )

        critical_bonus: float | None = None
        core_state = getattr(context, "core_state", None)
        if core_state is None:
            unresolved.append("Critical Healing requires canonical core_state")
        else:
            critical_trace = core_state.derived.get(StatId.CRITICAL_HEALING)
            if critical_trace is None:
                unresolved.append("Canonical Critical Healing stat is unavailable")
            else:
                critical_bonus = float(critical_trace.final_value)

        critical_multiplier: float | None = None
        critical_heal: float | None = None
        if critical_bonus is not None:
            critical_multiplier = 1.0 + self.BASE_CRITICAL_HEALING + critical_bonus
            if normal_heal is not None:
                critical_heal = normal_heal * critical_multiplier

        return ExtremeHealingEventResult(
            entity_id=str(entity_id),
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            critical_healing_bonus=critical_bonus,
            critical_multiplier=critical_multiplier,
            heal_coefficient_numbers=heal_numbers,
            tooltip_result=result,
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
