from __future__ import annotations

from dataclasses import replace
import re

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs
from .skill_line_repository import SkillLineRepository


class SorcererPassiveInputResolver:
    """Apply reviewed standing Sorcerer resource and power passives.

    Reviewed U50 ``Expert Summoner`` grants 5% Max Magicka and 5% Max Stamina.
    The separate 5% Max Health branch requires an explicitly active permanent pet
    and is intentionally left out of the standing resolver until that runtime
    condition is modeled separately.

    Reviewed U50 ``Expert Mage`` grants 108 Weapon and Spell Damage for each
    Sorcerer ability slotted on the active bar at max rank. The flat contribution
    belongs in the canonical Weapon/Spell Damage inputs so any heal whose
    coefficient scales from offensive power sees the result naturally.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Sorcerer can therefore lose one of its class lines, while
    a foreign base class can gain reviewed passive math only through explicitly
    equipped Sorcerer lines and separately proven passive ownership/rank.
    """

    DARK_MAGIC_ID = "dark_magic"
    DAEDRIC_SUMMONING_ID = "daedric_summoning"
    STORM_CALLING_ID = "storm_calling"
    SORCERER_LINE_IDS = frozenset({DARK_MAGIC_ID, DAEDRIC_SUMMONING_ID, STORM_CALLING_ID})
    EXPERT_SUMMONER_RESOURCE_PERCENT = 0.05
    EXPERT_MAGE_POWER_PER_SLOT = 108.0

    def __init__(self, skill_line_repository: SkillLineRepository | None = None) -> None:
        self.skill_line_repository = skill_line_repository

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def equipped_sorcerer_line_ids(cls, build: PlayerBuild) -> frozenset[str]:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return frozenset(explicit) & cls.SORCERER_LINE_IDS
        if str(build.EsoClass or "").strip().casefold() == "sorcerer":
            return cls.SORCERER_LINE_IDS
        return frozenset()

    def _active_sorcerer_slot_count(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
        equipped_lines: frozenset[str],
    ) -> tuple[int, tuple[str, ...]]:
        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        if self.skill_line_repository is None:
            if any(str(name or "").strip() for name in skills):
                return 0, (
                    "Sorcerer Expert Mage slot count is unresolved because the skill line repository is unavailable",
                )
            return 0, ()

        count = 0
        unresolved_names: list[str] = []
        for raw_name in skills:
            name = str(raw_name or "").strip()
            if not name:
                continue
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved_names.append(name)
                continue
            line_id = self._line_id(skill_line)
            if line_id in self.SORCERER_LINE_IDS and line_id in equipped_lines:
                count += 1

        unresolved: tuple[str, ...] = ()
        if unresolved_names:
            unresolved = (
                "Sorcerer Expert Mage slot count is unresolved because the active-bar "
                "skill line could not be resolved for: " + ", ".join(unresolved_names),
            )
        return count, unresolved

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        expert_summoner_owned: bool | None = None,
        expert_mage_owned: bool | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_sorcerer_line_ids(build)
        applied = result.applied_effect_count

        if self.DAEDRIC_SUMMONING_ID in equipped_lines and bool(expert_summoner_owned):
            magicka = PercentContribution(
                "Sorcerer: Expert Summoner",
                self.EXPERT_SUMMONER_RESOURCE_PERCENT,
            )
            stamina = PercentContribution(
                "Sorcerer: Expert Summoner",
                self.EXPERT_SUMMONER_RESOURCE_PERCENT,
            )
            result = replace(
                result,
                magicka=replace(
                    result.magicka,
                    skill_percent_contributions=(
                        *result.magicka.skill_percent_contributions,
                        magicka,
                    ),
                ),
                stamina=replace(
                    result.stamina,
                    skill_percent_contributions=(
                        *result.stamina.skill_percent_contributions,
                        stamina,
                    ),
                ),
            )
            applied += 2

        if self.STORM_CALLING_ID in equipped_lines and bool(expert_mage_owned):
            slot_count, unresolved = self._active_sorcerer_slot_count(
                build,
                active_bar=active_bar,
                equipped_lines=equipped_lines,
            )
            if unresolved:
                result = replace(
                    result,
                    unresolved=tuple(dict.fromkeys((*result.unresolved, *unresolved))),
                )
            if slot_count:
                bonus = self.EXPERT_MAGE_POWER_PER_SLOT * slot_count
                source = StatContribution("Sorcerer: Expert Mage", bonus)
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        weapon_damage=replace(
                            result.core.weapon_damage,
                            flat=(*result.core.weapon_damage.flat, source),
                        ),
                        spell_damage=replace(
                            result.core.spell_damage,
                            flat=(*result.core.spell_damage.flat, source),
                        ),
                    ),
                )
                applied += 2

        return replace(result, applied_effect_count=applied)
