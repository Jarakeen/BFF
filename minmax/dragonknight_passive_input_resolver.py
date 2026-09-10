from __future__ import annotations

from dataclasses import replace
import re

from models.build_model import PlayerBuild

from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs


class DragonknightPassiveInputResolver:
    """Apply reviewed standing Dragonknight passive stat contributions.

    Live-U50 ``A Soul Ablaze`` grants Healing Taken while Ardent Flame remains
    part of the character's equipped class-line route. Rank 1 grants 4% and rank
    2 grants 8%. The contribution belongs in canonical ``HEALING_TAKEN`` rather
    than Healing Done because it modifies heals received by the Dragonknight.

    Explicit ``PlayerBuild.ClassSkillLines`` are authoritative for subclass
    snapshots. A native Dragonknight can therefore lose Ardent Flame, while a
    foreign base class gains this passive only through an explicit Ardent Flame
    route and separately proven passive ownership/rank.
    """

    ARDENT_FLAME_ID = "ardent_flame"
    DRACONIC_POWER_ID = "draconic_power"
    EARTHEN_HEART_ID = "earthen_heart"
    DRAGONKNIGHT_LINE_IDS = frozenset(
        {ARDENT_FLAME_ID, DRACONIC_POWER_ID, EARTHEN_HEART_ID}
    )
    SOUL_ABLAZE_HEALING_TAKEN_BY_RANK = {
        1: 0.04,
        2: 0.08,
    }

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def equipped_dragonknight_line_ids(cls, build: PlayerBuild) -> frozenset[str]:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return frozenset(explicit) & cls.DRAGONKNIGHT_LINE_IDS
        if str(build.EsoClass or "").strip().casefold() == "dragonknight":
            return cls.DRAGONKNIGHT_LINE_IDS
        return frozenset()

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        soul_ablaze_rank: int | None = None,
    ) -> GearCalculationInputs:
        equipped_lines = self.equipped_dragonknight_line_ids(build)
        if self.ARDENT_FLAME_ID not in equipped_lines:
            return result
        if soul_ablaze_rank is None or int(soul_ablaze_rank) <= 0:
            return result

        rank = int(soul_ablaze_rank)
        value = self.SOUL_ABLAZE_HEALING_TAKEN_BY_RANK.get(rank)
        if value is None:
            return replace(
                result,
                unresolved=tuple(
                    dict.fromkeys(
                        (*result.unresolved, f"Unsupported A Soul Ablaze rank: {rank}")
                    )
                ),
            )

        source = StatContribution("Dragonknight: A Soul Ablaze", value)
        return replace(
            result,
            core=replace(
                result.core,
                healing_taken=replace(
                    result.core.healing_taken,
                    flat=(*result.core.healing_taken.flat, source),
                ),
            ),
            applied_effect_count=result.applied_effect_count + 1,
        )
