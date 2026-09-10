from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeArcanistHarnessedQuintessenceResult:
    weapon_spell_damage_bonus: float
    duration_seconds: float
    unresolved: tuple[str, ...]


class ExtremeArcanistHarnessedQuintessenceService:
    """Resolve reviewed U50 Harnessed Quintessence conditional power.

    Restoring Magicka or Stamina opens a 10-second Weapon/Spell Damage window.
    Rank 1 grants 142 and rank 2 grants 284. The caller must explicitly prove
    whether that post-resource-restoration window is active; this resolver never
    infers a trigger from ordinary recovery or from merely owning the passive.

    Explicit ``ClassSkillLines`` are authoritative for subclass snapshots.
    """

    PASSIVE_NAME = "Harnessed Quintessence"
    HERALD_OF_THE_TOME_ID = "herald_of_the_tome"
    POWER_BY_RANK = {1: 142.0, 2: 284.0}
    DURATION_SECONDS = 10.0

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
    def herald_of_the_tome_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.HERALD_OF_THE_TOME_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "arcanist"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        harnessed_quintessence_active: bool | None,
    ) -> ExtremeArcanistHarnessedQuintessenceResult:
        if not self.herald_of_the_tome_equipped(build):
            return ExtremeArcanistHarnessedQuintessenceResult(0.0, 0.0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeArcanistHarnessedQuintessenceResult(
                0.0,
                0.0,
                ("Harnessed Quintessence passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeArcanistHarnessedQuintessenceResult(
                0.0,
                0.0,
                ("Passive rank is not recorded for character: Harnessed Quintessence",),
            )
        rank = int(rank)
        if rank == 0:
            return ExtremeArcanistHarnessedQuintessenceResult(0.0, 0.0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeArcanistHarnessedQuintessenceResult(
                0.0,
                0.0,
                ("Passive max rank is not available in canonical data: Harnessed Quintessence",),
            )
        if rank < 0 or rank > int(maximum):
            return ExtremeArcanistHarnessedQuintessenceResult(
                0.0,
                0.0,
                (f"Invalid passive rank for Harnessed Quintessence: {rank}/{maximum}",),
            )
        power = self.POWER_BY_RANK.get(rank)
        if power is None:
            return ExtremeArcanistHarnessedQuintessenceResult(
                0.0,
                0.0,
                (f"Unsupported Harnessed Quintessence rank: {rank}",),
            )

        if harnessed_quintessence_active is None:
            return ExtremeArcanistHarnessedQuintessenceResult(
                0.0,
                0.0,
                ("Harnessed Quintessence requires explicit active buff-window state",),
            )
        if not isinstance(harnessed_quintessence_active, bool):
            raise ValueError(
                "harnessed_quintessence_active must be True, False, or None"
            )
        if not harnessed_quintessence_active:
            return ExtremeArcanistHarnessedQuintessenceResult(0.0, 0.0, ())

        return ExtremeArcanistHarnessedQuintessenceResult(
            weapon_spell_damage_bonus=power,
            duration_seconds=self.DURATION_SECONDS,
            unresolved=(),
        )
