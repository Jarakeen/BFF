from __future__ import annotations

from dataclasses import replace
from math import ceil

from minmax.build_calculation_context import BuildCalculationContext
from minmax.core_stat_calculator import CoreStatState
from minmax.derived_stats import DerivedStatTrace
from minmax.stat_ids import StatId


class ExtremeArcanistHarnessedQuintessenceContextService:
    """Insert reviewed Harnessed Quintessence flat power before percent scaling."""

    LABEL = "Arcanist: Harnessed Quintessence"

    @classmethod
    def _with_flat_bonus(
        cls,
        trace: DerivedStatTrace,
        bonus: float,
    ) -> DerivedStatTrace:
        value = float(bonus)
        if value < 0.0:
            raise ValueError("Harnessed Quintessence power bonus cannot be negative")
        if value == 0.0:
            return trace

        adjusted = DerivedStatTrace(stat=trace.stat)
        current = 0.0
        changed = False
        inserted = False
        raw_before_finalize: float | None = None

        for step_label, operation, operand, original_result in trace.steps:
            if not inserted and operation in {"multiply", "ceil", "retain"}:
                current += value
                adjusted.add(cls.LABEL, "add", value, current)
                inserted = True
                changed = True

            if not changed:
                current = float(original_result)
            elif operation == "set":
                current = float(operand)
            elif operation == "add":
                current += float(operand)
            elif operation == "multiply":
                current *= float(operand)
            elif operation == "ceil":
                raw_before_finalize = current
                current = float(ceil(current))
            elif operation == "retain":
                raw_before_finalize = current
            else:
                raise ValueError(
                    "Unsupported derived-stat trace operation while applying "
                    f"Harnessed Quintessence: {operation}"
                )

            adjusted.add(step_label, operation, float(operand), current)

        if not inserted:
            current += value
            adjusted.add(cls.LABEL, "add", value, current)
            raw_before_finalize = current

        adjusted.raw_value = (
            float(raw_before_finalize)
            if raw_before_finalize is not None
            else float(current)
        )
        adjusted.final_value = float(current)
        return adjusted

    def apply(
        self,
        context: BuildCalculationContext,
        *,
        weapon_spell_damage_bonus: float,
    ) -> BuildCalculationContext:
        bonus = float(weapon_spell_damage_bonus)
        if bonus < 0.0:
            raise ValueError("Harnessed Quintessence power bonus cannot be negative")
        if bonus == 0.0:
            return context

        core_state = context.core_state
        if core_state is None:
            raise ValueError("Harnessed Quintessence requires canonical core_state")

        weapon = core_state.derived.get(StatId.WEAPON_DAMAGE)
        spell = core_state.derived.get(StatId.SPELL_DAMAGE)
        if weapon is None or spell is None:
            raise ValueError(
                "Harnessed Quintessence requires canonical Weapon and Spell Damage traces"
            )

        derived = dict(core_state.derived)
        derived[StatId.WEAPON_DAMAGE] = self._with_flat_bonus(weapon, bonus)
        derived[StatId.SPELL_DAMAGE] = self._with_flat_bonus(spell, bonus)
        return replace(
            context,
            core_state=CoreStatState(
                base_character=core_state.base_character,
                derived=derived,
            ),
        )
