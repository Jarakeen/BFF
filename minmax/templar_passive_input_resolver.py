from __future__ import annotations

from dataclasses import replace
import re

from models.build_model import PlayerBuild

from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs


class TemplarPassiveInputResolver:
    """Apply reviewed standing Templar class-passive stat effects.

    Reviewed live-U50 ``Balanced Warrior`` grants 6% Weapon Damage, 6% Spell
    Damage, and 6% Armor at max rank. The offensive-power contribution belongs
    in the canonical Weapon/Spell Damage percent buckets so every downstream
    skill coefficient, including healing coefficients, sees the same value.

    Armor is deliberately not implemented here yet because this first consumer
    is MOST Actual Heal and Armor does not affect that objective. The omission is
    explicit rather than silently treating the whole passive as modeled for every
    future objective.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Templar may therefore lose Aedric Spear, while another
    base class can gain this reviewed passive only through an explicitly equipped
    Aedric Spear line plus separately proven passive ownership/rank.
    """

    AEDRIC_SPEAR_ID = "aedric_spear"
    DAWNS_WRATH_ID = "dawns_wrath"
    RESTORING_LIGHT_ID = "restoring_light"
    TEMPLAR_LINE_IDS = frozenset(
        {AEDRIC_SPEAR_ID, DAWNS_WRATH_ID, RESTORING_LIGHT_ID}
    )
    BALANCED_WARRIOR_POWER_PERCENT = 0.06

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def equipped_templar_line_ids(cls, build: PlayerBuild) -> frozenset[str]:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return frozenset(explicit) & cls.TEMPLAR_LINE_IDS
        if str(build.EsoClass or "").strip().casefold() == "templar":
            return cls.TEMPLAR_LINE_IDS
        return frozenset()

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        balanced_warrior_owned: bool | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_templar_line_ids(build)
        if (
            self.AEDRIC_SPEAR_ID not in equipped_lines
            or not bool(balanced_warrior_owned)
        ):
            return result

        contribution = StatContribution(
            "Templar: Balanced Warrior",
            self.BALANCED_WARRIOR_POWER_PERCENT,
        )
        return replace(
            result,
            core=replace(
                result.core,
                weapon_damage=replace(
                    result.core.weapon_damage,
                    percent=(*result.core.weapon_damage.percent, contribution),
                ),
                spell_damage=replace(
                    result.core.spell_damage,
                    percent=(*result.core.spell_damage.percent, contribution),
                ),
            ),
            applied_effect_count=result.applied_effect_count + 2,
        )
