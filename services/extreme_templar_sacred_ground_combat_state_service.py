from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeTemplarSacredGroundCombatStateResult:
    combat_state: CombatState
    minor_mending_active: bool
    unresolved: tuple[str, ...]


class ExtremeTemplarSacredGroundCombatStateService:
    """Resolve reviewed Templar Sacred Ground Minor Mending state.

    Sacred Ground grants Minor Mending while the character stands in their own
    Cleansing Ritual, Rune Focus, or Rite of Passage area. The post-area grace
    window is rank-dependent: up to two seconds at rank 1 and up to four seconds
    at rank 2. Both ranks grant the same Minor Mending effect while the reviewed
    window is active.

    The caller must explicitly state that the Sacred Ground window is active.
    This service never infers position or a recently-left grace window from merely
    owning Restoring Light. When future callers need to derive the window from
    timestamps, they must use the recorded passive rank to choose the correct
    duration before calling this resolver.

    Once legality is proven, Minor Mending is routed through ``CombatState`` so
    the canonical named-buff layer owns the +8% Healing Done semantics.
    """

    PASSIVE_NAME = "Sacred Ground"
    RESTORING_LIGHT_ID = "restoring_light"
    GRACE_SECONDS_BY_RANK = {1: 2.0, 2: 4.0}

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_line_repository: SkillLineRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path or get_data_dir() / "eso.db")
        self.skill_line_repository = skill_line_repository or SkillLineRepository(
            self.database_path
        )

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def restoring_light_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.RESTORING_LIGHT_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "templar"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        sacred_ground_window_active: bool = False,
    ) -> ExtremeTemplarSacredGroundCombatStateResult:
        if not sacred_ground_window_active:
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=CombatState(),
                minor_mending_active=False,
                unresolved=(),
            )

        base_state = CombatState(in_combat=True)
        if not self.restoring_light_equipped(build):
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=base_state,
                minor_mending_active=False,
                unresolved=(
                    "Sacred Ground scenario requires an equipped Restoring Light class line",
                ),
            )

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=base_state,
                minor_mending_active=False,
                unresolved=("Sacred Ground passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=base_state,
                minor_mending_active=False,
                unresolved=(
                    "Passive rank is not recorded for character: Sacred Ground",
                ),
            )
        if rank == 0:
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=base_state,
                minor_mending_active=False,
                unresolved=(),
            )

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=base_state,
                minor_mending_active=False,
                unresolved=(
                    "Passive max rank is not available in canonical data: Sacred Ground",
                ),
            )
        if rank not in self.GRACE_SECONDS_BY_RANK or rank > maximum:
            return ExtremeTemplarSacredGroundCombatStateResult(
                combat_state=base_state,
                minor_mending_active=False,
                unresolved=(
                    f"Unsupported passive rank: Sacred Ground {rank}/{maximum}",
                ),
            )

        return ExtremeTemplarSacredGroundCombatStateResult(
            combat_state=CombatState(in_combat=True, active_buffs=("Minor Mending",)),
            minor_mending_active=True,
            unresolved=(),
        )
