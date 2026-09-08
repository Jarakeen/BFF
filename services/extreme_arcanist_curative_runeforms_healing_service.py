from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeArcanistCurativeRuneformsHealingResult:
    multiplier: float
    unresolved: tuple[str, ...]


class ExtremeArcanistCurativeRuneformsHealingService:
    """Resolve reviewed Arcanist Healing Tides healing for Extreme builds.

    At reviewed U50 max rank, Healing Tides increases generic Healing Done by 4%
    for each active Crux. Crux is runtime state, so callers must explicitly supply
    the active count; this service never assumes a standing three-Crux condition.

    Explicit ``ClassSkillLines`` are authoritative for subclass snapshots. A pure
    Arcanist implicitly owns Curative Runeforms; another base class may use the
    passive only when Curative Runeforms is explicitly equipped and passive-rank
    evidence exists.
    """

    PASSIVE_NAME = "Healing Tides"
    CURATIVE_RUNEFORMS_ID = "curative_runeforms"
    HEALING_DONE_PER_CRUX = 0.04
    MAX_CRUX = 3

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
    def curative_runeforms_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.CURATIVE_RUNEFORMS_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "arcanist"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_crux: int | None,
    ) -> ExtremeArcanistCurativeRuneformsHealingResult:
        if not self.curative_runeforms_equipped(build):
            return ExtremeArcanistCurativeRuneformsHealingResult(1.0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeArcanistCurativeRuneformsHealingResult(
                1.0,
                ("Healing Tides passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeArcanistCurativeRuneformsHealingResult(
                1.0,
                ("Passive rank is not recorded for character: Healing Tides",),
            )
        if rank == 0:
            return ExtremeArcanistCurativeRuneformsHealingResult(1.0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeArcanistCurativeRuneformsHealingResult(
                1.0,
                ("Passive max rank is not available in canonical data: Healing Tides",),
            )
        if rank != maximum:
            return ExtremeArcanistCurativeRuneformsHealingResult(
                1.0,
                (f"Partial passive rank is not yet modeled: Healing Tides {rank}/{maximum}",),
            )

        if active_crux is None:
            return ExtremeArcanistCurativeRuneformsHealingResult(
                1.0,
                ("Healing Tides requires explicit active Crux state",),
            )
        try:
            count = int(active_crux)
        except (TypeError, ValueError) as exc:
            raise ValueError("active_crux must be an integer from 0 through 3") from exc
        if count != active_crux or not 0 <= count <= self.MAX_CRUX:
            raise ValueError("active_crux must be an integer from 0 through 3")

        return ExtremeArcanistCurativeRuneformsHealingResult(
            multiplier=1.0 + self.HEALING_DONE_PER_CRUX * count,
            unresolved=(),
        )
