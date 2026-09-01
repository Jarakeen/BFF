from __future__ import annotations

from collections import Counter
from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs
from .passive_math import (
    fighters_guild_slayer_weapon_spell_damage_percent,
    mages_guild_magicka_controller_percent,
)
from .skill_line_repository import SkillLineRepository


class GuildPassiveInputResolver:
    """Apply verified max-rank guild passives using active-bar slot counts."""

    MAGES_GUILD = "mages guild"
    FIGHTERS_GUILD = "fighters guild"

    def __init__(self, skill_line_repository: SkillLineRepository) -> None:
        self.skill_line_repository = skill_line_repository

    def _active_skill_line_counts(self, build: PlayerBuild, *, active_bar: str) -> Counter[str]:
        skills = build.BackBarSkills if str(active_bar or "front").casefold() == "back" else build.FrontBarSkills
        counts: Counter[str] = Counter()
        for raw_name in skills:
            name = str(raw_name or "").strip()
            if not name:
                continue
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line:
                counts[skill_line.casefold()] += 1
        return counts

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        mages_guild_passives_owned: bool = False,
        fighters_guild_passives_owned: bool = False,
        magicka_controller_owned: bool | None = None,
        slayer_owned: bool | None = None,
    ) -> GearCalculationInputs:
        mages_owned = mages_guild_passives_owned if magicka_controller_owned is None else magicka_controller_owned
        fighters_owned = fighters_guild_passives_owned if slayer_owned is None else slayer_owned
        if not (mages_owned or fighters_owned):
            return result

        counts = self._active_skill_line_counts(build, active_bar=active_bar)
        applied = result.applied_effect_count

        if mages_owned:
            bonus = mages_guild_magicka_controller_percent(counts[self.MAGES_GUILD])
            if bonus:
                max_magicka_source = PercentContribution("Mages Guild: Magicka Controller", bonus)
                recovery_source = PercentContribution("Mages Guild: Magicka Controller", bonus)
                result = replace(
                    result,
                    magicka=replace(
                        result.magicka,
                        skill_percent_contributions=result.magicka.skill_percent_contributions + (max_magicka_source,),
                    ),
                    magicka_recovery=replace(
                        result.magicka_recovery,
                        skill_percent_contributions=result.magicka_recovery.skill_percent_contributions + (recovery_source,),
                    ),
                )
                applied += 2

        if fighters_owned:
            bonus = fighters_guild_slayer_weapon_spell_damage_percent(counts[self.FIGHTERS_GUILD])
            if bonus:
                source = StatContribution("Fighters Guild: Slayer", bonus)
                result = replace(
                    result,
                    core=replace(
                        result.core,
                        weapon_damage=replace(
                            result.core.weapon_damage,
                            percent=result.core.weapon_damage.percent + (source,),
                        ),
                        spell_damage=replace(
                            result.core.spell_damage,
                            percent=result.core.spell_damage.percent + (source,),
                        ),
                    ),
                )
                applied += 2

        return replace(result, applied_effect_count=applied)
