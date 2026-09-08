from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeNecromancerLivingDeathHealingResult:
    multiplier: float
    unresolved: tuple[str, ...]


class ExtremeNecromancerLivingDeathHealingService:
    """Resolve reviewed Necromancer Curative Curse healing for Extreme builds.

    At reviewed max rank, Curative Curse increases generic Healing Done by 12%
    while the healer has a negative effect. The condition belongs to the healer,
    not the heal target, and the bonus is not restricted to Living Death heals.

    Explicit ``ClassSkillLines`` are authoritative for subclass snapshots. A
    pure Necromancer implicitly owns Living Death; another base class may use the
    passive only when Living Death is explicitly equipped and passive-rank
    evidence exists.
    """

    PASSIVE_NAME = "Curative Curse"
    LIVING_DEATH_ID = "living_death"
    HEALING_DONE_MULTIPLIER = 1.12

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
    def living_death_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.LIVING_DEATH_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "necromancer"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        has_negative_effect: bool | None,
    ) -> ExtremeNecromancerLivingDeathHealingResult:
        if not self.living_death_equipped(build):
            return ExtremeNecromancerLivingDeathHealingResult(1.0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeNecromancerLivingDeathHealingResult(
                1.0,
                ("Curative Curse passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeNecromancerLivingDeathHealingResult(
                1.0,
                ("Passive rank is not recorded for character: Curative Curse",),
            )
        if rank == 0:
            return ExtremeNecromancerLivingDeathHealingResult(1.0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeNecromancerLivingDeathHealingResult(
                1.0,
                ("Passive max rank is not available in canonical data: Curative Curse",),
            )
        if rank != maximum:
            return ExtremeNecromancerLivingDeathHealingResult(
                1.0,
                (
                    f"Partial passive rank is not yet modeled: Curative Curse {rank}/{maximum}",
                ),
            )

        if has_negative_effect is None:
            return ExtremeNecromancerLivingDeathHealingResult(
                1.0,
                ("Curative Curse requires explicit healer negative-effect state",),
            )
        if not has_negative_effect:
            return ExtremeNecromancerLivingDeathHealingResult(1.0, ())
        return ExtremeNecromancerLivingDeathHealingResult(
            self.HEALING_DONE_MULTIPLIER,
            (),
        )
