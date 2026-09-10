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
class ExtremeDragonknightElderDragonCombatStateResult:
    combat_state: CombatState
    minor_brutality_active: bool
    unresolved: tuple[str, ...]


class ExtremeDragonknightElderDragonCombatStateService:
    """Resolve live-U50 Elder Dragon Minor Brutality state.

    Activating a Draconic Power ability grants Minor Brutality for 20 seconds at
    either learned rank. The passive's separate missing-Health-based Health
    Recovery branch does not alter one healing-event magnitude and is therefore
    outside this resolver's MOST Actual Heal responsibility.

    The caller must explicitly prove that the Elder Dragon window is active. No
    Draconic Power cast or uptime is inferred from the build. Once legality is
    proven, Minor Brutality is routed through CombatState so the canonical named
    buff layer owns the +10% Weapon Damage semantics before heal coefficients are
    evaluated.
    """

    PASSIVE_NAME = "Elder Dragon"
    DRACONIC_POWER_ID = "draconic_power"
    REVIEWED_DURATION_SECONDS = 20.0

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
    def draconic_power_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.DRACONIC_POWER_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "dragonknight"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        elder_dragon_window_active: bool = False,
    ) -> ExtremeDragonknightElderDragonCombatStateResult:
        if not elder_dragon_window_active:
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=CombatState(),
                minor_brutality_active=False,
                unresolved=(),
            )

        base_state = CombatState(in_combat=True)
        if not self.draconic_power_equipped(build):
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=base_state,
                minor_brutality_active=False,
                unresolved=(
                    "Elder Dragon scenario requires an equipped Draconic Power class line",
                ),
            )

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=base_state,
                minor_brutality_active=False,
                unresolved=("Elder Dragon passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=base_state,
                minor_brutality_active=False,
                unresolved=(
                    "Passive rank is not recorded for character: Elder Dragon",
                ),
            )
        if rank == 0:
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=base_state,
                minor_brutality_active=False,
                unresolved=(),
            )

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=base_state,
                minor_brutality_active=False,
                unresolved=(
                    "Passive max rank is not available in canonical data: Elder Dragon",
                ),
            )
        if rank < 0 or rank > maximum:
            return ExtremeDragonknightElderDragonCombatStateResult(
                combat_state=base_state,
                minor_brutality_active=False,
                unresolved=(f"Invalid passive rank for Elder Dragon: {rank}/{maximum}",),
            )

        return ExtremeDragonknightElderDragonCombatStateResult(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=("Minor Brutality",),
            ),
            minor_brutality_active=True,
            unresolved=(),
        )
