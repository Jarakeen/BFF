from __future__ import annotations

from dataclasses import replace
import re

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .gear_stat_inputs import GearCalculationInputs
from .skill_line_repository import SkillLineRepository


class NightbladePassiveInputResolver:
    """Apply reviewed Nightblade standing passives to shared character inputs.

    Reviewed Update 46+ ``Magicka Flood`` grants 6% Max Magicka and Max Stamina
    while at least one Siphoning ability is slotted on the active bar. The bonus
    belongs in the primary-resource percentage bucket so it combines additively
    with other percentage sources before ESO rounding.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Nightblade can therefore lose Siphoning, while another
    base class can gain the reviewed passive only when Siphoning is explicitly
    equipped and passive ownership/rank has been proven by the caller.
    """

    SIPHONING_ID = "siphoning"
    NIGHTBLADE_LINE_IDS = frozenset({"assassination", "shadow", SIPHONING_ID})
    MAGICKA_FLOOD_PERCENT = 0.06

    def __init__(self, skill_line_repository: SkillLineRepository) -> None:
        self.skill_line_repository = skill_line_repository

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def equipped_nightblade_line_ids(cls, build: PlayerBuild) -> frozenset[str]:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return frozenset(explicit) & cls.NIGHTBLADE_LINE_IDS
        if str(build.EsoClass or "").strip().casefold() == "nightblade":
            return cls.NIGHTBLADE_LINE_IDS
        return frozenset()

    def _active_bar_has_siphoning(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> tuple[bool, tuple[str, ...]]:
        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        unresolved_names: list[str] = []
        for raw_name in skills:
            name = str(raw_name or "").strip()
            if not name:
                continue
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved_names.append(name)
                continue
            if self._line_id(skill_line) == self.SIPHONING_ID:
                return True, ()

        if unresolved_names:
            return False, (
                "Nightblade Magicka Flood trigger is unresolved because the active-bar "
                "skill line could not be resolved for: " + ", ".join(unresolved_names),
            )
        return False, ()

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        magicka_flood_owned: bool | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_nightblade_line_ids(build)
        if self.SIPHONING_ID not in equipped_lines or not bool(magicka_flood_owned):
            return result

        has_siphoning, unresolved = self._active_bar_has_siphoning(
            build,
            active_bar=active_bar,
        )
        if not has_siphoning:
            if not unresolved:
                return result
            return replace(
                result,
                unresolved=tuple(dict.fromkeys((*result.unresolved, *unresolved))),
            )

        magicka_source = PercentContribution(
            "Nightblade: Magicka Flood",
            self.MAGICKA_FLOOD_PERCENT,
        )
        stamina_source = PercentContribution(
            "Nightblade: Magicka Flood",
            self.MAGICKA_FLOOD_PERCENT,
        )
        return replace(
            result,
            magicka=replace(
                result.magicka,
                skill_percent_contributions=(
                    *result.magicka.skill_percent_contributions,
                    magicka_source,
                ),
            ),
            stamina=replace(
                result.stamina,
                skill_percent_contributions=(
                    *result.stamina.skill_percent_contributions,
                    stamina_source,
                ),
            ),
            applied_effect_count=result.applied_effect_count + 1,
        )
