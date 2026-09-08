from __future__ import annotations

"""Extreme/MOST Bash objective adapter.

The actual Bash equations remain owned by ``minmax.formulas.final_calculations``.
This service adds two pieces Extreme needs around those formulas:

* explicit dual-bar One Hand and Shield legality for the MOST Bashy recipe; and
* fail-closed source-channel accounting so an unresolved Bash modifier is never
  silently treated as a proven zero.

Numeric fields are optional on purpose. A missing field contributes zero only to
an explicitly partial reviewed-value calculation and is simultaneously retained
as a blocker. A complete result requires every formula channel to be supplied.
"""

from dataclasses import dataclass, fields

from minmax.character_build.weapon_type import (
    WeaponSkillLine,
    WeaponType,
    resolve_weapon_skill_line,
)
from minmax.formulas.final_calculations import calculate_bash_cost, calculate_bash_damage


@dataclass(frozen=True)
class ExtremeBashBarWeapons:
    main_hand: WeaponType
    off_hand: WeaponType = WeaponType.NONE

    @property
    def skill_line(self) -> WeaponSkillLine | None:
        try:
            return resolve_weapon_skill_line(self.main_hand, self.off_hand)
        except ValueError:
            return None

    @property
    def is_one_hand_and_shield(self) -> bool:
        return self.skill_line is WeaponSkillLine.ONE_HAND_AND_SHIELD


@dataclass(frozen=True)
class ExtremeBashLegalityContext:
    front: ExtremeBashBarWeapons
    back: ExtremeBashBarWeapons

    @property
    def dual_bar_one_hand_and_shield(self) -> bool:
        return self.front.is_one_hand_and_shield and self.back.is_one_hand_and_shield

    def blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if not self.front.is_one_hand_and_shield:
            blockers.append("front bar is not a legal One Hand and Shield configuration")
        if not self.back.is_one_hand_and_shield:
            blockers.append("back bar is not a legal One Hand and Shield configuration")
        return tuple(blockers)


@dataclass(frozen=True)
class ExtremeBashDamageInputs:
    spell_resist: float | None = None
    physical_resist: float | None = None
    cp_bash_damage: float | None = None
    skill2_bash_damage: float | None = None
    physical_damage_done: float | None = None
    damage_done: float | None = None
    direct_damage_done: float | None = None
    single_target_damage_done: float | None = None
    skill_bash_damage: float | None = None
    set_extra_bash_damage: float | None = None
    skill_extra_bash_damage: float | None = None
    item_extra_bash_damage: float | None = None


@dataclass(frozen=True)
class ExtremeBashCostInputs:
    item_bash_cost: float | None = None
    cp_bash_cost: float | None = None
    skill_bash_cost: float | None = None
    set_bash_cost: float | None = None


@dataclass(frozen=True)
class ExtremeBashObjectiveResult:
    objective_key: str
    reviewed_value: float
    unresolved_channels: tuple[str, ...]
    legality_blockers: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved_channels and not self.legality_blockers


class ExtremeBashObjectiveService:
    """Evaluate reviewed Bash channels without overclaiming missing mechanics."""

    @staticmethod
    def _resolved_values(inputs) -> tuple[dict[str, float], tuple[str, ...]]:
        values: dict[str, float] = {}
        unresolved: list[str] = []
        for field in fields(inputs):
            value = getattr(inputs, field.name)
            if value is None:
                values[field.name] = 0.0
                unresolved.append(field.name)
            else:
                values[field.name] = float(value)
        return values, tuple(unresolved)

    @classmethod
    def evaluate_damage(
        cls,
        inputs: ExtremeBashDamageInputs,
        *,
        legality: ExtremeBashLegalityContext | None = None,
    ) -> ExtremeBashObjectiveResult:
        values, unresolved = cls._resolved_values(inputs)
        legality_blockers = () if legality is None else legality.blockers()
        return ExtremeBashObjectiveResult(
            objective_key="bash_damage",
            reviewed_value=calculate_bash_damage(**values),
            unresolved_channels=unresolved,
            legality_blockers=legality_blockers,
        )

    @classmethod
    def evaluate_cost(
        cls,
        inputs: ExtremeBashCostInputs,
        *,
        legality: ExtremeBashLegalityContext | None = None,
    ) -> ExtremeBashObjectiveResult:
        values, unresolved = cls._resolved_values(inputs)
        legality_blockers = () if legality is None else legality.blockers()
        return ExtremeBashObjectiveResult(
            objective_key="bash_cost",
            reviewed_value=calculate_bash_cost(**values),
            unresolved_channels=unresolved,
            legality_blockers=legality_blockers,
        )
