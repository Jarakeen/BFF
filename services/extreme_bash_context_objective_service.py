from __future__ import annotations

"""Evaluate Extreme/MOST Bash against the full saved-build calculation context.

Bash damage depends on the larger of final Physical and Spell Resistance. Those
values already belong to ``BuildCalculationContextFactory`` because that pipeline
owns armor bases/traits, shields, Mundus, Champion Points, gear sets, race/class/
armor/weapon passives, and other reviewed static build inputs.

This adapter deliberately does not duplicate any of that resistance math. It
copies the two final resistance values into the existing Bash objective and
preserves unresolved build effects as explicit blockers.
"""

from dataclasses import dataclass, replace

from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_build.weapon_type import WeaponType
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild

from .extreme_bash_build_objective_service import (
    ExtremeBashBuildObjectiveResult,
    ExtremeBashBuildObjectiveService,
)
from .extreme_bash_champion_point_service import ExtremeBashChampionPointResult
from .extreme_bash_jewelry_service import ExtremeBashJewelryResult
from .extreme_bash_objective_service import (
    ExtremeBashBarWeapons,
    ExtremeBashDamageInputs,
    ExtremeBashLegalityContext,
)


@dataclass(frozen=True)
class ExtremeBashContextObjectiveResult:
    objective: ExtremeBashBuildObjectiveResult
    physical_resistance: float | None
    spell_resistance: float | None
    context_blockers: tuple[str, ...] = ()

    @property
    def reviewed_value(self) -> float:
        return self.objective.reviewed_value

    @property
    def mechanic_complete(self) -> bool:
        return self.objective.mechanic_complete and not self.context_blockers


class ExtremeBashContextObjectiveService:
    """Project the real calculated build resistance into the Bash formula."""

    _ONE_HANDED = {
        "sword": WeaponType.SWORD,
        "axe": WeaponType.AXE,
        "mace": WeaponType.MACE,
        "dagger": WeaponType.DAGGER,
    }

    @classmethod
    def _saved_bar_weapons(cls, build: PlayerBuild, bar: str) -> ExtremeBashBarWeapons:
        main, offhand = build.active_weapon_slots(bar)
        main_key = str(main.WeaponType or "").strip().casefold()
        offhand_key = str(offhand.WeaponType or "").strip().casefold()

        # Legacy saves stored the whole skill-line family in the main-hand slot.
        # The concrete sword here is only a legality surrogate; Bash math does
        # not depend on one-handed subtype in this adapter.
        if main_key == "one hand and shield" and offhand.is_empty:
            return ExtremeBashBarWeapons(WeaponType.SWORD, WeaponType.SHIELD)

        main_type = cls._ONE_HANDED.get(main_key, WeaponType.NONE)
        offhand_type = WeaponType.SHIELD if offhand_key == "shield" else WeaponType.NONE
        return ExtremeBashBarWeapons(main_type, offhand_type)

    @classmethod
    def legality_for_build(cls, build: PlayerBuild) -> ExtremeBashLegalityContext:
        return ExtremeBashLegalityContext(
            front=cls._saved_bar_weapons(build, "front"),
            back=cls._saved_bar_weapons(build, "back"),
        )

    @classmethod
    def evaluate_context(
        cls,
        context: BuildCalculationContext,
        inputs: ExtremeBashDamageInputs,
        *,
        legality: ExtremeBashLegalityContext | None = None,
        champion_point: ExtremeBashChampionPointResult | None = None,
        jewelry: ExtremeBashJewelryResult | None = None,
    ) -> ExtremeBashContextObjectiveResult:
        if inputs.physical_resist is not None or inputs.spell_resist is not None:
            raise ValueError(
                "Bash resistance was supplied directly and through BuildCalculationContext"
            )

        physical: float | None = None
        spell: float | None = None
        blockers: list[str] = []
        resolved_inputs = inputs

        if context.core_state is None:
            blockers.append("BuildCalculationContext has no core stat state for Bash resistance")
        else:
            physical_state = context.core_state.derived.get(StatId.PHYSICAL_RESISTANCE)
            spell_state = context.core_state.derived.get(StatId.SPELL_RESISTANCE)
            if physical_state is None:
                blockers.append("BuildCalculationContext has no Physical Resistance result")
            else:
                physical = float(physical_state.final_value)
            if spell_state is None:
                blockers.append("BuildCalculationContext has no Spell Resistance result")
            else:
                spell = float(spell_state.final_value)

            resolved_inputs = replace(
                resolved_inputs,
                physical_resist=physical,
                spell_resist=spell,
            )

        blockers.extend(
            f"Build context: {problem}" for problem in context.unresolved_gear_effects
        )

        objective = ExtremeBashBuildObjectiveService.evaluate_damage(
            resolved_inputs,
            legality=legality,
            champion_point=champion_point,
            jewelry=jewelry,
        )
        return ExtremeBashContextObjectiveResult(
            objective=objective,
            physical_resistance=physical,
            spell_resistance=spell,
            context_blockers=tuple(blockers),
        )

    @classmethod
    def evaluate_build(
        cls,
        factory: BuildCalculationContextFactory,
        *,
        character_id: str,
        build_id: str,
        build: PlayerBuild,
        progression: CharacterProgression,
        inputs: ExtremeBashDamageInputs,
        champion_point: ExtremeBashChampionPointResult | None = None,
        jewelry: ExtremeBashJewelryResult | None = None,
        active_bar: str = "front",
    ) -> ExtremeBashContextObjectiveResult:
        context = factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        return cls.evaluate_context(
            context,
            inputs,
            legality=cls.legality_for_build(build),
            champion_point=champion_point,
            jewelry=jewelry,
        )
