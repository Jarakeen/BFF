from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeNightbladeSiphoningHealingResult:
    multiplier: float
    siphoning_slots: int
    unresolved: tuple[str, ...]


class ExtremeNightbladeSiphoningHealingService:
    """Resolve reviewed Soul Siphoner healing for Extreme builds.

    Soul Siphoner is generic Healing Done at reviewed max rank: each Siphoning
    ability slotted on the active bar increases healing done by 3%. Unlike
    Emerald Moss, the resulting multiplier is not limited to Siphoning heals.

    Explicit ``ClassSkillLines`` remain authoritative for subclass snapshots. A
    pure Nightblade implicitly owns its native Siphoning line, while another
    base class may use this reviewed passive only when Siphoning is explicitly
    equipped and passive-rank evidence is supplied by progression.

    Missing passive-rank or slotted-skill-line evidence preserves a numeric lower
    bound and returns an explicit blocker instead of assuming the unknown
    contribution is zero.
    """

    PASSIVE_NAME = "Soul Siphoner"
    SIPHONING_ID = "siphoning"
    HEALING_DONE_PER_SLOTTED_ABILITY = 0.03

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
    def siphoning_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.SIPHONING_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "nightblade"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_bar: str = "front",
    ) -> ExtremeNightbladeSiphoningHealingResult:
        if not self.siphoning_equipped(build):
            return ExtremeNightbladeSiphoningHealingResult(1.0, 0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeNightbladeSiphoningHealingResult(
                1.0,
                0,
                ("Soul Siphoner passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeNightbladeSiphoningHealingResult(
                1.0,
                0,
                ("Passive rank is not recorded for character: Soul Siphoner",),
            )
        if rank == 0:
            return ExtremeNightbladeSiphoningHealingResult(1.0, 0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeNightbladeSiphoningHealingResult(
                1.0,
                0,
                ("Passive max rank is not available in canonical data: Soul Siphoner",),
            )
        if rank != maximum:
            return ExtremeNightbladeSiphoningHealingResult(
                1.0,
                0,
                (f"Partial passive rank is not yet modeled: Soul Siphoner {rank}/{maximum}",),
            )

        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        count = 0
        unresolved: list[str] = []
        for raw_name in skills:
            name = str(raw_name or "").strip()
            if not name:
                continue
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved.append(
                    "Soul Siphoner slot count: could not resolve canonical skill line "
                    f"for slotted ability {name!r} on {active_bar} bar"
                )
                continue
            if self._line_id(skill_line) == self.SIPHONING_ID:
                count += 1

        multiplier = 1.0 + self.HEALING_DONE_PER_SLOTTED_ABILITY * count
        return ExtremeNightbladeSiphoningHealingResult(
            multiplier=multiplier,
            siphoning_slots=count,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
