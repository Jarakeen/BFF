from __future__ import annotations

from collections import Counter
from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs
from .passive_math import (
    warden_advanced_species_crit_damage,
    warden_flourish_recovery_percent,
    warden_frozen_armor_resistance,
)
from .skill_line_repository import SkillLineRepository


class WardenPassiveInputResolver:
    """Apply verified standing Warden passives to shared character inputs.

    The math in passive_math.py is max-rank math. Explicit ownership flags let
    production character progression activate only passives known to be maxed.
    ``None`` preserves the historical direct-call behavior for compatibility.
    """

    ANIMAL_COMPANIONS = "animal companions"
    GREEN_BALANCE = "green balance"
    WINTERS_EMBRACE = "winter's embrace"
    WARDEN_LINES = frozenset({ANIMAL_COMPANIONS, GREEN_BALANCE, WINTERS_EMBRACE})

    def __init__(self, skill_line_repository: SkillLineRepository) -> None:
        self.skill_line_repository = skill_line_repository

    def _active_skill_line_counts(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> tuple[Counter[str], tuple[str, ...]]:
        skills = build.BackBarSkills if str(active_bar or "front").casefold() == "back" else build.FrontBarSkills
        counts: Counter[str] = Counter()
        unresolved: list[str] = []

        for raw_name in skills:
            name = str(raw_name or "").strip()
            if not name:
                continue
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved.append(
                    f"Warden passive math: could not resolve canonical skill line for slotted ability {name!r} on {active_bar} bar"
                )
                continue
            key = skill_line.casefold()
            if key in self.WARDEN_LINES:
                counts[key] += 1

        return counts, tuple(unresolved)

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        flourish_owned: bool | None = None,
        advanced_species_owned: bool | None = None,
        frozen_armor_owned: bool | None = None,
    ) -> GearCalculationInputs:
        if str(build.EsoClass or "").strip().casefold() != "warden":
            return result

        # Historical callers did not provide per-passive ownership. Keep that
        # behavior only when all three flags are omitted. Production saved-build
        # progression supplies explicit booleans.
        legacy_assumption = all(
            value is None
            for value in (flourish_owned, advanced_species_owned, frozen_armor_owned)
        )
        flourish_owned = legacy_assumption if flourish_owned is None else flourish_owned
        advanced_species_owned = legacy_assumption if advanced_species_owned is None else advanced_species_owned
        frozen_armor_owned = legacy_assumption if frozen_armor_owned is None else frozen_armor_owned

        counts, passive_unresolved = self._active_skill_line_counts(build, active_bar=active_bar)
        unresolved = result.unresolved + passive_unresolved
        applied = result.applied_effect_count

        animal_count = counts[self.ANIMAL_COMPANIONS]
        winter_count = counts[self.WINTERS_EMBRACE]

        if flourish_owned:
            flourish = warden_flourish_recovery_percent(animal_count)
            if flourish:
                source = PercentContribution("Warden: Flourish", flourish)
                result = replace(
                    result,
                    magicka_recovery=replace(
                        result.magicka_recovery,
                        skill_percent_contributions=result.magicka_recovery.skill_percent_contributions + (source,),
                    ),
                    stamina_recovery=replace(
                        result.stamina_recovery,
                        skill_percent_contributions=result.stamina_recovery.skill_percent_contributions + (source,),
                    ),
                )
                applied += 2

        if advanced_species_owned:
            advanced_species = warden_advanced_species_crit_damage(animal_count)
            if advanced_species:
                contribution = StatContribution("Warden: Advanced Species", advanced_species)
                critical_damage = replace(
                    result.core.critical_damage,
                    additive_after_percent=result.core.critical_damage.additive_after_percent + (contribution,),
                )
                result = replace(result, core=replace(result.core, critical_damage=critical_damage))
                applied += 1

        if frozen_armor_owned:
            frozen_armor = warden_frozen_armor_resistance(winter_count)
            if frozen_armor:
                contribution = StatContribution("Warden: Frozen Armor", frozen_armor)
                physical = replace(
                    result.core.physical_resistance,
                    flat=result.core.physical_resistance.flat + (contribution,),
                )
                spell = replace(
                    result.core.spell_resistance,
                    flat=result.core.spell_resistance.flat + (contribution,),
                )
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        physical_resistance=physical,
                        spell_resistance=spell,
                    ),
                )
                applied += 2

        return replace(
            result,
            applied_effect_count=applied,
            unresolved=unresolved,
        )
