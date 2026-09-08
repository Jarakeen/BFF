from __future__ import annotations

from dataclasses import replace
import re

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .gear_stat_inputs import GearCalculationInputs


class SorcererPassiveInputResolver:
    """Apply reviewed standing Sorcerer resource passives.

    Reviewed U50 ``Expert Summoner`` grants 5% Max Magicka and 5% Max Stamina.
    The separate 5% Max Health branch requires an explicitly active permanent pet
    and is intentionally left out of the standing resolver until that runtime
    condition is modeled separately.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Sorcerer can therefore lose Daedric Summoning, while a
    foreign base class can gain the reviewed passive only when Daedric Summoning
    is explicitly equipped and passive ownership/rank is proven by the caller.
    """

    DAEDRIC_SUMMONING_ID = "daedric_summoning"
    SORCERER_LINE_IDS = frozenset({"dark_magic", DAEDRIC_SUMMONING_ID, "storm_calling"})
    EXPERT_SUMMONER_RESOURCE_PERCENT = 0.05

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

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        expert_summoner_owned: bool | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_sorcerer_line_ids(build)
        if self.DAEDRIC_SUMMONING_ID not in equipped_lines or not bool(expert_summoner_owned):
            return result

        magicka = PercentContribution(
            "Sorcerer: Expert Summoner",
            self.EXPERT_SUMMONER_RESOURCE_PERCENT,
        )
        stamina = PercentContribution(
            "Sorcerer: Expert Summoner",
            self.EXPERT_SUMMONER_RESOURCE_PERCENT,
        )
        return replace(
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
            applied_effect_count=result.applied_effect_count + 2,
        )
