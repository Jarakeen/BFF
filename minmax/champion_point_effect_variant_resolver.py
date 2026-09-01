from __future__ import annotations

import re
from pathlib import Path

from .champion_point_static_repository import ChampionPointStaticRepository
from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .support_effect_category import SupportEffectCategory
from .support_target_type import SupportTargetType


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


class ChampionPointEffectVariantResolver:
    """Resolve audited dynamic/support CP mechanics into EffectVariants.

    Static character-sheet CP effects remain owned by
    ChampionPointStaticRepository + StaticBuildInputResolver. This resolver
    intentionally covers only CP mechanics that belong in the dynamic
    EffectVariant pipeline.
    """

    _FROM_THE_BRINK_POINTS = (10, 20, 30, 40, 50)
    _FROM_THE_BRINK_PER_STAGE = 2200.0
    _FROM_THE_BRINK_DURATION = 6.0
    _FROM_THE_BRINK_COOLDOWN = 30.0
    _FROM_THE_BRINK_HEALTH_THRESHOLD = 25.0

    def __init__(
        self,
        database_path: str | Path,
        *,
        static_repository: ChampionPointStaticRepository | None = None,
    ) -> None:
        self.repository = static_repository or ChampionPointStaticRepository(
            database_path
        )

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _clean_description(value: str) -> str:
        return " ".join(_COLOR.sub("", value or "").split())

    @staticmethod
    def _stages(points: int, thresholds: tuple[int, ...], max_points: int) -> int:
        allocated = max(0, min(int(points), int(max_points)))
        return sum(1 for threshold in thresholds if allocated >= threshold)

    def resolve(
        self,
        name: str,
        points: int,
    ) -> tuple[tuple[EffectVariant, ...], tuple[str, ...]]:
        key = self._key(name)
        if key != "from the brink":
            return (), ()

        record = self.repository.get(name)
        if record is None:
            return (), ("Dynamic Champion Point not found: From the Brink",)

        expected_jumps = (0,) + self._FROM_THE_BRINK_POINTS
        description = self._clean_description(record.description)
        expected_fragments = (
            "under 25% Health",
            "2200 damage per stage",
            "for 6 seconds",
            "once every 30 seconds per target",
        )

        if (
            record.max_points != 50
            or tuple(record.jump_points) != expected_jumps
            or any(fragment.casefold() not in description.casefold() for fragment in expected_fragments)
        ):
            return (), (
                "Dynamic Champion Point source no longer matches verified mapping: From the Brink",
            )

        stages = self._stages(
            points,
            self._FROM_THE_BRINK_POINTS,
            record.max_points,
        )
        if stages <= 0:
            return (), ()

        magnitude = self._FROM_THE_BRINK_PER_STAGE * stages
        return (
            (
                EffectVariant(
                    name="damage_shield",
                    layer=EffectLayer.PROC,
                    source="Champion Point: From the Brink",
                    magnitude=magnitude,
                    duration=self._FROM_THE_BRINK_DURATION,
                    cooldown=self._FROM_THE_BRINK_COOLDOWN,
                    target_count=1,
                    scaling=(
                        "2200 shield per purchased stage; stages at "
                        "10/20/30/40/50 points"
                    ),
                    condition=(
                        "heal_self_or_ally_below_25_percent_health; "
                        "30_second_cooldown_per_target"
                    ),
                    trigger="on_heal_target_below_25_percent_health",
                    target_type=SupportTargetType.ALLY,
                    category=SupportEffectCategory.BUFF,
                ),
            ),
            (),
        )
