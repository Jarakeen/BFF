from __future__ import annotations

from dataclasses import dataclass, replace

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
    critical_healing: DerivedStatInputs = DerivedStatInputs()
    critical_chance: DerivedStatInputs = DerivedStatInputs()
    critical_resistance: DerivedStatInputs = DerivedStatInputs()
    healing_done: DerivedStatInputs = DerivedStatInputs()
    healing_taken: DerivedStatInputs = DerivedStatInputs()


@dataclass(frozen=True)
class CoreStatState:
    base_character: BaseCharacterState
    derived: dict[StatId, DerivedStatTrace]


class CoreStatCalculator:
    """Aggregate foundational combat stats without inventing unresolved ESO rules."""

    # Verified naked level-50 baselines used by the ESO character sheet.
    # Critical Healing is the character-sheet bonus above ESO's inherent
    # critical-heal multiplier, so its displayed standing baseline is 0%.
    VERIFIED_BASES = {
        StatId.WEAPON_CRITICAL: 0.10,
        StatId.SPELL_CRITICAL: 0.10,
        StatId.CRITICAL_CHANCE: 0.10,
        StatId.CRITICAL_DAMAGE: 0.50,
        StatId.CRITICAL_HEALING: 0.0,
        StatId.CRITICAL_RESISTANCE: 1320.0,
    }

    def __init__(self) -> None:
        self._derived = DerivedStatCalculator()

    @staticmethod
    def _with_race_stat(inputs: DerivedStatInputs, race_stats: dict[str, float], stat: StatId) -> DerivedStatInputs:
        value = float(race_stats.get(stat.value, 0.0))
        if not value:
            return inputs
        return replace(
            inputs,
            flat=inputs.flat + (StatContribution("race", value),),
        )

    def calculate(
        self,
        *,
        character_progression: CharacterProgression,
        base_character: BaseCharacterState,
        race_stats: dict[str, float] | None = None,
        inputs: CoreStatInputs = CoreStatInputs(),
    ) -> CoreStatState:
        """Return base character and derived stats with data-driven race contributions."""
        _ = character_progression
        race_stats = race_stats or {}

        resolved = CoreStatInputs(
            weapon_damage=self._with_race_stat(inputs.weapon_damage, race_stats, StatId.WEAPON_DAMAGE),
            spell_damage=self._with_race_stat(inputs.spell_damage, race_stats, StatId.SPELL_DAMAGE),
            physical_resistance=self._with_race_stat(inputs.physical_resistance, race_stats, StatId.PHYSICAL_RESISTANCE),
            spell_resistance=self._with_race_stat(inputs.spell_resistance, race_stats, StatId.SPELL_RESISTANCE),
            physical_penetration=self._with_race_stat(inputs.physical_penetration, race_stats, StatId.PHYSICAL_PENETRATION),
            spell_penetration=self._with_race_stat(inputs.spell_penetration, race_stats, StatId.SPELL_PENETRATION),
            weapon_critical=self._with_race_stat(inputs.weapon_critical, race_stats, StatId.WEAPON_CRITICAL),
            spell_critical=self._with_race_stat(inputs.spell_critical, race_stats, StatId.SPELL_CRITICAL),
            critical_damage=self._with_race_stat(inputs.critical_damage, race_stats, StatId.CRITICAL_DAMAGE),
            critical_healing=self._with_race_stat(inputs.critical_healing, race_stats, StatId.CRITICAL_HEALING),
            critical_chance=self._with_race_stat(inputs.critical_chance, race_stats, StatId.CRITICAL_CHANCE),
            critical_resistance=self._with_race_stat(inputs.critical_resistance, race_stats, StatId.CRITICAL_RESISTANCE),
            healing_done=self._with_race_stat(inputs.healing_done, race_stats, StatId.HEALING_DONE),
            healing_taken=self._with_race_stat(inputs.healing_taken, race_stats, StatId.HEALING_TAKEN),
        )

        pairs = (
            (StatId.WEAPON_DAMAGE, resolved.weapon_damage),
            (StatId.SPELL_DAMAGE, resolved.spell_damage),
            (StatId.PHYSICAL_RESISTANCE, resolved.physical_resistance),
            (StatId.SPELL_RESISTANCE, resolved.spell_resistance),
            (StatId.PHYSICAL_PENETRATION, resolved.physical_penetration),
            (StatId.SPELL_PENETRATION, resolved.spell_penetration),
            (StatId.WEAPON_CRITICAL, resolved.weapon_critical),
            (StatId.SPELL_CRITICAL, resolved.spell_critical),
            (StatId.CRITICAL_DAMAGE, resolved.critical_damage),
            (StatId.CRITICAL_HEALING, resolved.critical_healing),
            (StatId.CRITICAL_CHANCE, resolved.critical_chance),
            (StatId.CRITICAL_RESISTANCE, resolved.critical_resistance),
            (StatId.HEALING_DONE, resolved.healing_done),
            (StatId.HEALING_TAKEN, resolved.healing_taken),
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
        derived[StatId.WEAPON_DAMAGE] = self._derived.weapon_damage(resolved.weapon_damage)
        derived[StatId.SPELL_DAMAGE] = self._derived.spell_damage(resolved.spell_damage)

        return CoreStatState(base_character=base_character, derived=derived)
