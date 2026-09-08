from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeArcanistFatedFortuneCriticalHealingResult:
    critical_healing_bonus: float
    duration_seconds: float
    unresolved: tuple[str, ...]


class ExtremeArcanistFatedFortuneCriticalHealingService:
    """Resolve reviewed U50 Fated Fortune critical-healing state.

    At max rank, Fated Fortune grants 12% Critical Damage and Critical Healing
    for 7 seconds after the Arcanist generates or consumes Crux. This resolver
    models only whether that buff window is already active. It deliberately does
    not assume that a heal which itself consumes Crux benefits from the buff it
    triggers on that same event; that ordering belongs in the event layer and
    must remain fail-closed until proven.

    Explicit ``ClassSkillLines`` are authoritative for subclass snapshots. A
    pure Arcanist implicitly owns Herald of the Tome only when no explicit route
    is supplied; a foreign class may gain the passive through an explicit Herald
    of the Tome subclass route.
    """

    PASSIVE_NAME = "Fated Fortune"
    HERALD_OF_THE_TOME_ID = "herald_of_the_tome"
    CRITICAL_HEALING_BONUS = 0.12
    DURATION_SECONDS = 7.0

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
        fated_fortune_active: bool | None,
    ) -> ExtremeArcanistFatedFortuneCriticalHealingResult:
        if not self.herald_of_the_tome_equipped(build):
            return ExtremeArcanistFatedFortuneCriticalHealingResult(0.0, 0.0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(
                0.0,
                0.0,
                ("Fated Fortune passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(
                0.0,
                0.0,
                ("Passive rank is not recorded for character: Fated Fortune",),
            )
        if rank == 0:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(0.0, 0.0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(
                0.0,
                0.0,
                ("Passive max rank is not available in canonical data: Fated Fortune",),
            )
        if rank != maximum:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(
                0.0,
                0.0,
                (f"Partial passive rank is not yet modeled: Fated Fortune {rank}/{maximum}",),
            )

        if fated_fortune_active is None:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(
                0.0,
                0.0,
                ("Fated Fortune requires explicit active buff-window state",),
            )
        if not isinstance(fated_fortune_active, bool):
            raise ValueError("fated_fortune_active must be True, False, or None")
        if not fated_fortune_active:
            return ExtremeArcanistFatedFortuneCriticalHealingResult(0.0, 0.0, ())

        return ExtremeArcanistFatedFortuneCriticalHealingResult(
            critical_healing_bonus=self.CRITICAL_HEALING_BONUS,
            duration_seconds=self.DURATION_SECONDS,
            unresolved=(),
        )
