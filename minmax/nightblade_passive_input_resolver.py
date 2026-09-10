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
    while at least one Siphoning ability is slotted on the active bar. Reviewed
    live-U50 ``Dark Vigor`` grants 5% Max Health for each Shadow ability slotted
    on the active bar at max rank. These bonuses belong in the primary-resource
    percentage bucket so downstream coefficient math sees one canonical result.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Nightblade can therefore lose Siphoning or Shadow, while
    another base class can gain reviewed passive math only when the exact line is
    explicitly equipped and passive ownership/rank has been proven by the caller.
    """

    ASSASSINATION_ID = "assassination"
    SHADOW_ID = "shadow"
    SIPHONING_ID = "siphoning"
    NIGHTBLADE_LINE_IDS = frozenset(
        {ASSASSINATION_ID, SHADOW_ID, SIPHONING_ID}
    )
    MAGICKA_FLOOD_PERCENT = 0.06
    DARK_VIGOR_HEALTH_PERCENT_PER_SHADOW_SLOT = 0.05

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

    @staticmethod
    def _active_skills(build: PlayerBuild, *, active_bar: str) -> tuple[str, ...]:
        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        return tuple(
            str(raw_name or "").strip()
            for raw_name in skills
            if str(raw_name or "").strip()
        )

    def _active_bar_has_siphoning(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> tuple[bool, tuple[str, ...]]:
        unresolved_names: list[str] = []
        for name in self._active_skills(build, active_bar=active_bar):
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

    def _active_shadow_slot_count(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> tuple[int, tuple[str, ...]]:
        count = 0
        unresolved_names: list[str] = []
        for name in self._active_skills(build, active_bar=active_bar):
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved_names.append(name)
                continue
            if self._line_id(skill_line) == self.SHADOW_ID:
                count += 1

        unresolved: tuple[str, ...] = ()
        if unresolved_names:
            unresolved = (
                "Nightblade Dark Vigor slot count is unresolved because the active-bar "
                "skill line could not be resolved for: " + ", ".join(unresolved_names),
            )
        return count, unresolved

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        magicka_flood_owned: bool | None = None,
        dark_vigor_owned: bool | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_nightblade_line_ids(build)
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count

        if self.SIPHONING_ID in equipped_lines and bool(magicka_flood_owned):
            has_siphoning, siphoning_unresolved = self._active_bar_has_siphoning(
                build,
                active_bar=active_bar,
            )
            unresolved.extend(siphoning_unresolved)
            if has_siphoning:
                magicka_source = PercentContribution(
                    "Nightblade: Magicka Flood",
                    self.MAGICKA_FLOOD_PERCENT,
                )
                stamina_source = PercentContribution(
                    "Nightblade: Magicka Flood",
                    self.MAGICKA_FLOOD_PERCENT,
                )
                result = replace(
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
                )
                applied += 1

        if self.SHADOW_ID in equipped_lines and bool(dark_vigor_owned):
            shadow_slots, shadow_unresolved = self._active_shadow_slot_count(
                build,
                active_bar=active_bar,
            )
            unresolved.extend(shadow_unresolved)
            if shadow_slots:
                health_source = PercentContribution(
                    "Nightblade: Dark Vigor",
                    self.DARK_VIGOR_HEALTH_PERCENT_PER_SHADOW_SLOT * shadow_slots,
                )
                result = replace(
                    result,
                    health=replace(
                        result.health,
                        skill_percent_contributions=(
                            *result.health.skill_percent_contributions,
                            health_source,
                        ),
                    ),
                )
                applied += 1

        return replace(
            result,
            applied_effect_count=applied,
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
