from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeWardenAcceleratedGrowthCombatStateResult:
    combat_state: CombatState
    major_mending_active: bool
    active_window_seconds: float | None
    unresolved: tuple[str, ...]


class ExtremeWardenAcceleratedGrowthCombatStateService:
    """Resolve an explicitly proven Accelerated Growth Major Mending window.

    Accelerated Growth triggers after a Green Balance heal lands on the caster or
    an ally below 40% Health. Both reviewed ranks grant Major Mending; rank 1 keeps
    the window for 2 seconds and rank 2 for 4 seconds. The triggering heal itself
    is not assumed to benefit from the newly granted buff. This service represents
    a subsequent heal while the caller-proven window is already active.

    Once legal, the named buff is routed through ``CombatState`` so canonical
    Healing Done math owns Major Mending's magnitude and stacking semantics. No
    active window is inferred merely from owning Green Balance or the passive.
    """

    PASSIVE_NAME = "Accelerated Growth"
    GREEN_BALANCE_ID = "green_balance"
    WINDOW_SECONDS_BY_RANK = {1: 2.0, 2: 4.0}

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def green_balance_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.GREEN_BALANCE_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "warden"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        accelerated_growth_window_active: bool = False,
    ) -> ExtremeWardenAcceleratedGrowthCombatStateResult:
        if not accelerated_growth_window_active:
            return ExtremeWardenAcceleratedGrowthCombatStateResult(
                combat_state=CombatState(),
                major_mending_active=False,
                active_window_seconds=None,
                unresolved=(),
            )

        base_state = CombatState(in_combat=True)
        if not self.green_balance_equipped(build):
            return ExtremeWardenAcceleratedGrowthCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                active_window_seconds=None,
                unresolved=(
                    "Accelerated Growth scenario requires an equipped Green Balance class line",
                ),
            )

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeWardenAcceleratedGrowthCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                active_window_seconds=None,
                unresolved=("Accelerated Growth passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeWardenAcceleratedGrowthCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                active_window_seconds=None,
                unresolved=(
                    "Passive rank is not recorded for character: Accelerated Growth",
                ),
            )
        rank = int(rank)
        if rank == 0:
            return ExtremeWardenAcceleratedGrowthCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                active_window_seconds=None,
                unresolved=(),
            )
        duration = self.WINDOW_SECONDS_BY_RANK.get(rank)
        if duration is None:
            return ExtremeWardenAcceleratedGrowthCombatStateResult(
                combat_state=base_state,
                major_mending_active=False,
                active_window_seconds=None,
                unresolved=(f"Unsupported Accelerated Growth passive rank: {rank}",),
            )

        return ExtremeWardenAcceleratedGrowthCombatStateResult(
            combat_state=CombatState(in_combat=True, active_buffs=("Major Mending",)),
            major_mending_active=True,
            active_window_seconds=duration,
            unresolved=(),
        )
