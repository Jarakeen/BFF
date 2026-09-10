from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeTemplarRestoringLightHealingResult:
    multiplier: float
    unresolved: tuple[str, ...]


class ExtremeTemplarRestoringLightHealingService:
    """Resolve reviewed Templar Mending healing for Extreme builds.

    Reviewed live Mending increases the healing effects of Restoring Light
    abilities in proportion to the severity of the target's wounds. Rank 1
    reaches up to 6% and rank 2 reaches up to 13%. This service models that
    wording linearly against missing-health fraction: a full-health target
    receives no Mending bonus and a theoretical zero-health fraction reaches
    the active rank's maximum.

    The passive is an ability-family modifier, not generic Healing Done. It must
    therefore never increase Restoration Staff, guild, or other class-line heals.

    Explicit ``ClassSkillLines`` are authoritative for subclass snapshots. A
    pure Templar implicitly owns Restoring Light; a foreign base class may use
    Mending only when Restoring Light is explicitly equipped and passive-rank
    evidence exists. Missing rank or ability-line evidence preserves the known
    lower bound and returns an explicit blocker.
    """

    PASSIVE_NAME = "Mending"
    RESTORING_LIGHT_ID = "restoring_light"
    RANK_MAX_HEALING_BONUS = {
        1: 0.06,
        2: 0.13,
    }

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
        ability_name: str,
        target_health_fraction: float | None,
    ) -> ExtremeTemplarRestoringLightHealingResult:
        ability_line = self.skill_line_repository.skill_line_for_ability_name(
            str(ability_name or "").strip()
        )
        if ability_line is None:
            return ExtremeTemplarRestoringLightHealingResult(
                1.0,
                (
                    "Mending ability family: could not resolve canonical skill line "
                    f"for ability {str(ability_name or '').strip()!r}",
                ),
            )
        if self._line_id(ability_line) != self.RESTORING_LIGHT_ID:
            return ExtremeTemplarRestoringLightHealingResult(1.0, ())
        if not self.restoring_light_equipped(build):
            return ExtremeTemplarRestoringLightHealingResult(1.0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeTemplarRestoringLightHealingResult(
                1.0,
                ("Mending passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeTemplarRestoringLightHealingResult(
                1.0,
                ("Passive rank is not recorded for character: Mending",),
            )
        if rank == 0:
            return ExtremeTemplarRestoringLightHealingResult(1.0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeTemplarRestoringLightHealingResult(
                1.0,
                ("Passive max rank is not available in canonical data: Mending",),
            )
        if maximum != max(self.RANK_MAX_HEALING_BONUS):
            return ExtremeTemplarRestoringLightHealingResult(
                1.0,
                (
                    "Canonical passive max rank is not supported for Mending: "
                    f"{maximum}",
                ),
            )

        rank_maximum = self.RANK_MAX_HEALING_BONUS.get(rank)
        if rank_maximum is None or rank > maximum:
            return ExtremeTemplarRestoringLightHealingResult(
                1.0,
                (f"Passive rank is not supported for Mending: {rank}/{maximum}",),
            )

        if target_health_fraction is None:
            return ExtremeTemplarRestoringLightHealingResult(1.0, ())

        target_health_fraction = float(target_health_fraction)
        if not 0.0 <= target_health_fraction <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")

        missing_health_fraction = 1.0 - target_health_fraction
        return ExtremeTemplarRestoringLightHealingResult(
            multiplier=1.0 + rank_maximum * missing_health_fraction,
            unresolved=(),
        )
