from __future__ import annotations

"""Resolve reviewed standing weapon-passive power for Extreme MOST Actual Heal.

H1 already evaluates weapon base power and weapon traits through canonical build
math. This service supplies the remaining *standing passive* Weapon/Spell Damage
change for the active weapon configuration, then expresses that change as an
effective highest-offensive-power delta for the existing component-level healing
calculator.

The values are U50-reviewed mechanics already established by the Extreme weapon
passive audits. Conditional damage, critical chance, sustain, movement, block, and
Heavy-Attack states remain outside this standing H1 layer.
"""

from dataclasses import dataclass
from math import ceil
from pathlib import Path

from minmax.character_build.weapon_type import (
    WeaponSkillLine,
    WeaponType,
    resolve_weapon_skill_line,
)
from minmax.eso_weapon_type_id import weapon_type_from_saved_name
from minmax.item_base_stats import WEAPON_POWER_CP160_GOLD
from minmax.skill_line_repository import SkillLineRepository
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


TWIN_BLADE_SWORD_DAMAGE_PER_SWORD = 64.0
AMBIDEXTROUS_OFFHAND_POWER_PERCENT = 0.03
SWORD_AND_BOARD_POWER_PERCENT = 0.03
HEAVY_WEAPONS_GREATSWORD_DAMAGE = 129.0


@dataclass(frozen=True)
class ExtremeActualHealWeaponPassivePowerResult:
    power_bonus: float
    sources: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealWeaponPassivePowerService:
    """Project reviewed standing weapon passives into H1 effective power."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        skill_line_repository: SkillLineRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.skill_lines = skill_line_repository or SkillLineRepository(self.database_path)

    def _passive_maxed(self, progression, passive_name: str) -> tuple[bool, tuple[str, ...]]:
        if progression is None:
            return False, (f"{passive_name} requires character progression evidence",)
        rank = progression.passive_rank(passive_name)
        if rank is None:
            return False, (f"Passive rank is not recorded for character: {passive_name}",)
        if rank == 0:
            return False, ()
        maximum = self.skill_lines.passive_max_rank(passive_name)
        if maximum is None:
            return False, (f"Passive max rank is not available in canonical data: {passive_name}",)
        if rank != maximum:
            return False, (f"Partial passive rank is not yet modeled: {passive_name} {rank}/{maximum}",)
        return True, ()

    @staticmethod
    def _active_weapon_configuration(build: PlayerBuild, active_bar: str):
        main, offhand = build.active_weapon_slots(active_bar)
        main_type = weapon_type_from_saved_name(main.WeaponType)
        offhand_type = weapon_type_from_saved_name(offhand.WeaponType) if offhand.WeaponType else WeaponType.NONE
        if main_type is None:
            if not str(main.WeaponType or "").strip():
                return None, main, offhand, ()
            return None, main, offhand, (
                f"active {active_bar} weapon type is unresolved: {main.WeaponType}",
            )
        if offhand_type is None:
            return None, main, offhand, (
                f"active {active_bar} off-hand weapon type is unresolved: {offhand.WeaponType}",
            )
        try:
            line = resolve_weapon_skill_line(main_type, offhand_type)
        except ValueError as exc:
            return None, main, offhand, (str(exc),)
        return (line, main_type, offhand_type), main, offhand, ()

    @staticmethod
    def _trace_shape(trace) -> tuple[float, float, float]:
        """Return pre-percent flat value, current additive multiplier, after-flat.

        DerivedStatCalculator records the exact percentage multiplier in its trace.
        Weapon/Spell Damage currently has no reviewed additive-after-percent sources,
        but preserving the final post-percent additions here makes the projection
        fail less spectacularly if one is added later.
        """
        steps = tuple(getattr(trace, "steps", ()) or ())
        multiply_index = next(
            (
                index
                for index, (_label, operation, _value, _result) in enumerate(steps)
                if operation == "multiply"
            ),
            None,
        )
        if multiply_index is None:
            # No percentage bucket was active. For current Weapon/Spell Damage
            # inputs, raw_value is therefore the pre-percent flat total.
            return float(getattr(trace, "raw_value", trace.final_value)), 1.0, 0.0

        previous_result = (
            float(steps[multiply_index - 1][3])
            if multiply_index > 0
            else 0.0
        )
        multiplier = float(steps[multiply_index][2])
        after = 0.0
        for _label, operation, value, _result in steps[multiply_index + 1 :]:
            if operation == "add":
                after += float(value)
        return previous_result, multiplier, after

    @classmethod
    def _project_trace_delta(
        cls,
        trace,
        *,
        flat_power: float,
        added_percent: float,
    ) -> float:
        pre_percent, multiplier, after = cls._trace_shape(trace)
        new_raw = (pre_percent + float(flat_power)) * (
            multiplier + float(added_percent)
        ) + after
        return float(ceil(new_raw)) - float(trace.final_value)

    def resolve(
        self,
        *,
        build: PlayerBuild,
        context,
        active_bar: str = "front",
    ) -> ExtremeActualHealWeaponPassivePowerResult:
        bar = "back" if str(active_bar or "front").casefold() == "back" else "front"
        configuration, _main_slot, _offhand_slot, configuration_unresolved = (
            self._active_weapon_configuration(build, bar)
        )
        if configuration is None:
            return ExtremeActualHealWeaponPassivePowerResult(
                power_bonus=0.0,
                unresolved=configuration_unresolved,
            )

        line, main_type, offhand_type = configuration
        progression = getattr(context, "progression", None)
        flat_power = 0.0
        added_percent = 0.0
        sources: list[str] = []
        unresolved: list[str] = []

        if line is WeaponSkillLine.DUAL_WIELD:
            maxed, problems = self._passive_maxed(progression, "Twin Blade and Blunt")
            unresolved.extend(problems)
            if maxed:
                swords = int(main_type is WeaponType.SWORD) + int(offhand_type is WeaponType.SWORD)
                if swords:
                    flat_power += TWIN_BLADE_SWORD_DAMAGE_PER_SWORD * swords
                    sources.append(
                        f"Twin Blade and Blunt: {swords} sword(s)"
                    )

            maxed, problems = self._passive_maxed(progression, "Ambidextrous")
            unresolved.extend(problems)
            if maxed:
                offhand_name = str(getattr(_offhand_slot, "WeaponType", "") or "").strip()
                offhand_power = WEAPON_POWER_CP160_GOLD.get(offhand_name)
                if offhand_power is None:
                    unresolved.append(
                        f"Ambidextrous off-hand weapon power is unavailable: {offhand_name or '(empty)'}"
                    )
                else:
                    flat_power += float(offhand_power) * AMBIDEXTROUS_OFFHAND_POWER_PERCENT
                    sources.append("Ambidextrous")

        elif line is WeaponSkillLine.ONE_HAND_AND_SHIELD:
            maxed, problems = self._passive_maxed(progression, "Sword and Board")
            unresolved.extend(problems)
            if maxed:
                added_percent += SWORD_AND_BOARD_POWER_PERCENT
                sources.append("Sword and Board")

        elif line is WeaponSkillLine.TWO_HANDED:
            maxed, problems = self._passive_maxed(progression, "Heavy Weapons")
            unresolved.extend(problems)
            if maxed and main_type is WeaponType.GREATSWORD:
                flat_power += HEAVY_WEAPONS_GREATSWORD_DAMAGE
                sources.append("Heavy Weapons: Greatsword")

        core_state = getattr(context, "core_state", None)
        if core_state is None:
            if flat_power or added_percent:
                unresolved.append("standing weapon passive power requires canonical core_state")
            return ExtremeActualHealWeaponPassivePowerResult(
                power_bonus=0.0,
                sources=tuple(sources),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        weapon_trace = core_state.derived.get(StatId.WEAPON_DAMAGE)
        spell_trace = core_state.derived.get(StatId.SPELL_DAMAGE)
        if weapon_trace is None or spell_trace is None:
            if flat_power or added_percent:
                unresolved.append(
                    "standing weapon passive power requires canonical Weapon and Spell Damage traces"
                )
            return ExtremeActualHealWeaponPassivePowerResult(
                power_bonus=0.0,
                sources=tuple(sources),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        if not flat_power and not added_percent:
            return ExtremeActualHealWeaponPassivePowerResult(
                power_bonus=0.0,
                sources=(),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        current_highest = max(
            float(weapon_trace.final_value),
            float(spell_trace.final_value),
        )
        new_weapon = float(weapon_trace.final_value) + self._project_trace_delta(
            weapon_trace,
            flat_power=flat_power,
            added_percent=added_percent,
        )
        new_spell = float(spell_trace.final_value) + self._project_trace_delta(
            spell_trace,
            flat_power=flat_power,
            added_percent=added_percent,
        )
        bonus = max(new_weapon, new_spell) - current_highest

        return ExtremeActualHealWeaponPassivePowerResult(
            power_bonus=float(bonus),
            sources=tuple(sources),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "AMBIDEXTROUS_OFFHAND_POWER_PERCENT",
    "ExtremeActualHealWeaponPassivePowerResult",
    "ExtremeActualHealWeaponPassivePowerService",
    "HEAVY_WEAPONS_GREATSWORD_DAMAGE",
    "SWORD_AND_BOARD_POWER_PERCENT",
    "TWIN_BLADE_SWORD_DAMAGE_PER_SWORD",
]
