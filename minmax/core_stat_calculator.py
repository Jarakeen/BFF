from __future__ import annotations

from dataclasses import dataclass

from .base_character_state import BaseCharacterState
from .character_progression import CharacterProgression
from .derived_stats import DerivedStatCalculator, DerivedStatInputs, DerivedStatTrace, StatContribution
from .stat_ids import StatId


@dataclass(frozen=True)
class CoreStatInputs:
    """Resolved build contributions for the foundational combat statistics.

    This layer deliberately contains no ESO item/set lookup logic. Callers
    resolve those contributions first, then pass them here for a traceable
    calculation.
    """

    weapon_damage: DerivedStatInputs = DerivedStatInputs()
    spell_damage: DerivedStatInputs = DerivedStatInputs()
    physical_resistance: DerivedStatInputs = DerivedStatInputs()
    spell_resistance: DerivedStatInputs = DerivedStatInputs()
    physical_penetration: DerivedStatInputs = DerivedStatInputs()
    spell_penetration: DerivedStatInputs = DerivedStatInputs()
    weapon_critical: DerivedStatInputs = DerivedStatInputs()
    spell_critical: DerivedStatInputs = DerivedStatInputs()
    critical_damage: DerivedStatInputs = DerivedStatInputs()
    critical_chance: DerivedStatInputs = DerivedStatInputs()
    critical_resistance: DerivedStatInputs = DerivedStatInputs()
    healing_done: DerivedStatInputs = DerivedStatInputs()
    healing_taken: DerivedStatInputs = DerivedStatInputs()


@dataclass(frozen=True)
class CoreStatState:
    base_character: BaseCharacterState
    derived: dict[StatId, DerivedStatTrace]


class CoreStatCalculator:
    """Aggregate 2C foundational combat stats without inventing unresolved ESO rules."""

    # Update-50/level-50 UESP baseline values from the project's equations:
    # crit chance starts at 10%, crit damage at 50%, and crit resistance at
    # 1320 before item/set/skill/CP/buff contributions are applied.
    VERIFIED_BASES = {
        StatId.CRITICAL_CHANCE: 0.10,
        StatId.CRITICAL_DAMAGE: 0.50,
        StatId.CRITICAL_RESISTANCE: 1320.0,
    }

    def __init__(self) -> None:
        self._derived = DerivedStatCalculator()

    def calculate(
        self,
        *,
        character_progression: CharacterProgression,
        base_character: BaseCharacterState,
        inputs: CoreStatInputs = CoreStatInputs(),
    ) -> CoreStatState:
        """Return the base character state plus traceable derived stat results."""
        _ = character_progression

        pairs = (
            (StatId.WEAPON_DAMAGE, inputs.weapon_damage),
            (StatId.SPELL_DAMAGE, inputs.spell_damage),
            (StatId.PHYSICAL_RESISTANCE, inputs.physical_resistance),
            (StatId.SPELL_RESISTANCE, inputs.spell_resistance),
            (StatId.PHYSICAL_PENETRATION, inputs.physical_penetration),
            (StatId.SPELL_PENETRATION, inputs.spell_penetration),
            (StatId.WEAPON_CRITICAL, inputs.weapon_critical),
            (StatId.SPELL_CRITICAL, inputs.spell_critical),
            (StatId.CRITICAL_DAMAGE, inputs.critical_damage),
            (StatId.CRITICAL_CHANCE, inputs.critical_chance),
            (StatId.CRITICAL_RESISTANCE, inputs.critical_resistance),
            (StatId.HEALING_DONE, inputs.healing_done),
            (StatId.HEALING_TAKEN, inputs.healing_taken),
        )

        derived = {}
        for stat, stat_inputs in pairs:
            base = self.VERIFIED_BASES.get(stat, 0.0)
            derived[stat] = self._derived.resolved_stat(
                stat,
                base=base,
                inputs=stat_inputs,
            )

        # Weapon/Spell Damage have an established level baseline and therefore
        # use their specific calculators rather than the generic zero-base path.
        derived[StatId.WEAPON_DAMAGE] = self._derived.weapon_damage(inputs.weapon_damage)
        derived[StatId.SPELL_DAMAGE] = self._derived.spell_damage(inputs.spell_damage)

        return CoreStatState(base_character=base_character, derived=derived)
