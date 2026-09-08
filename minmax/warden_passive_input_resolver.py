from __future__ import annotations

from collections import Counter
from dataclasses import replace
import re

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

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A Warden can therefore lose a native line's passives when that
    line is replaced, while another base class can gain reviewed Warden-line
    passive math when that exact line is equipped and passive-rank evidence is
    supplied by progression.
    """

    ANIMAL_COMPANIONS = "animal companions"
    GREEN_BALANCE = "green balance"
    WINTERS_EMBRACE = "winter's embrace"
    WARDEN_LINES = frozenset({ANIMAL_COMPANIONS, GREEN_BALANCE, WINTERS_EMBRACE})

    ANIMAL_COMPANIONS_ID = "animal_companions"
    GREEN_BALANCE_ID = "green_balance"
    WINTERS_EMBRACE_ID = "winters_embrace"
    WARDEN_LINE_IDS = frozenset(
        {ANIMAL_COMPANIONS_ID, GREEN_BALANCE_ID, WINTERS_EMBRACE_ID}
    )

    def __init__(self, skill_line_repository: SkillLineRepository) -> None:
        self.skill_line_repository = skill_line_repository

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def equipped_warden_line_ids(cls, build: PlayerBuild) -> frozenset[str]:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return frozenset(explicit) & cls.WARDEN_LINE_IDS
        if str(build.EsoClass or "").strip().casefold() == "warden":
            return cls.WARDEN_LINE_IDS
        return frozenset()

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
            line_id = self._line_id(skill_line)
            if line_id == self.ANIMAL_COMPANIONS_ID:
                counts[self.ANIMAL_COMPANIONS] += 1
            elif line_id == self.GREEN_BALANCE_ID:
                counts[self.GREEN_BALANCE] += 1
            elif line_id == self.WINTERS_EMBRACE_ID:
                counts[self.WINTERS_EMBRACE] += 1

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
        equipped_lines = self.equipped_warden_line_ids(build)
        if not equipped_lines:
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

        # A passive cannot survive removal of its owning class line. Conversely,
        # an explicitly equipped foreign Warden line can use the passive only
        # when the caller separately proves passive ownership/rank.
        flourish_owned = bool(flourish_owned) and self.ANIMAL_COMPANIONS_ID in equipped_lines
        advanced_species_owned = bool(advanced_species_owned) and self.ANIMAL_COMPANIONS_ID in equipped_lines
        frozen_armor_owned = bool(frozen_armor_owned) and self.WINTERS_EMBRACE_ID in equipped_lines

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
