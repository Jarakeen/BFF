from __future__ import annotations

from collections import Counter
from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import PercentContribution
from .gear_stat_inputs import GearCalculationInputs
from .passive_math import support_magicka_aid_recovery_percent
from .skill_line_repository import SkillLineRepository


class AllianceSupportPassiveInputResolver:
    """Apply verified standing Alliance War Support passives.

    Only Magicka Aid belongs in generic standing stats. Combat Medic depends on
    keep proximity and Battle Resurrection depends on PvP resurrection state,
    so both remain outside this layer.
    """

    SUPPORT = "support"

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
        support_passives_owned: bool = False,
    ) -> GearCalculationInputs:
        if not support_passives_owned:
            return result

        counts = self._active_skill_line_counts(build, active_bar=active_bar)
        bonus = support_magicka_aid_recovery_percent(counts[self.SUPPORT])
        if not bonus:
            return result

        source = PercentContribution("Support: Magicka Aid", bonus)
        return replace(
            result,
            magicka_recovery=replace(
                result.magicka_recovery,
                skill_percent_contributions=result.magicka_recovery.skill_percent_contributions + (source,),
            ),
            applied_effect_count=result.applied_effect_count + 1,
        )
