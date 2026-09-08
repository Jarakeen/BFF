from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild
from services.extreme_necromancer_living_death_healing_service import (
    ExtremeNecromancerLivingDeathHealingService,
)


@dataclass(frozen=True)
class ExtremeNecromancerNearDeathExperienceResult:
    critical_chance_bonus: float
    living_death_slotted: bool
    unresolved: tuple[str, ...]


class ExtremeNecromancerNearDeathExperienceService:
    """Resolve reviewed Near-Death Experience healing critical chance.

    At reviewed max rank, Near-Death Experience increases Critical Strike Chance
    with all healing abilities by up to 12% in proportion to the severity of the
    target's wounds while at least one Living Death ability is slotted on the
    active bar.

    This is a probability modifier, not a critical-heal magnitude modifier. It
    therefore must not increase ``critical_heal`` in MOST Actual Heal, whose
    critical result already asks how large the event is if an eligible component
    crits.

    Explicit ``ClassSkillLines`` remain authoritative for subclass snapshots. A
    pure Necromancer implicitly owns Living Death; a foreign base class may use
    the passive only when Living Death is explicitly equipped and passive-rank
    evidence exists.
    """

    PASSIVE_NAME = "Near-Death Experience"
    LIVING_DEATH_ID = "living_death"
    MAX_HEALING_CRITICAL_CHANCE_BONUS = 0.12

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
        return ExtremeNecromancerLivingDeathHealingService._line_id(value)

    @classmethod
    def living_death_equipped(cls, build: PlayerBuild) -> bool:
        return ExtremeNecromancerLivingDeathHealingService.living_death_equipped(build)

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        target_health_fraction: float | None,
        active_bar: str = "front",
    ) -> ExtremeNecromancerNearDeathExperienceResult:
        if not self.living_death_equipped(build):
            return ExtremeNecromancerNearDeathExperienceResult(0.0, False, ())

        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        living_death_slotted = False
        unresolved_slots: list[str] = []
        for raw_name in skills:
            name = str(raw_name or "").strip()
            if not name:
                continue
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved_slots.append(
                    "Near-Death Experience slot condition: could not resolve canonical "
                    f"skill line for slotted ability {name!r} on {active_bar} bar"
                )
                continue
            if self._line_id(skill_line) == self.LIVING_DEATH_ID:
                living_death_slotted = True

        if not living_death_slotted:
            if unresolved_slots:
                return ExtremeNecromancerNearDeathExperienceResult(
                    0.0,
                    False,
                    tuple(dict.fromkeys(unresolved_slots)),
                )
            return ExtremeNecromancerNearDeathExperienceResult(0.0, False, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeNecromancerNearDeathExperienceResult(
                0.0,
                True,
                ("Near-Death Experience passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeNecromancerNearDeathExperienceResult(
                0.0,
                True,
                ("Passive rank is not recorded for character: Near-Death Experience",),
            )
        if rank == 0:
            return ExtremeNecromancerNearDeathExperienceResult(0.0, True, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeNecromancerNearDeathExperienceResult(
                0.0,
                True,
                (
                    "Passive max rank is not available in canonical data: "
                    "Near-Death Experience",
                ),
            )
        if rank != maximum:
            return ExtremeNecromancerNearDeathExperienceResult(
                0.0,
                True,
                (
                    "Partial passive rank is not yet modeled: "
                    f"Near-Death Experience {rank}/{maximum}",
                ),
            )

        if target_health_fraction is None:
            return ExtremeNecromancerNearDeathExperienceResult(
                0.0,
                True,
                (
                    "Near-Death Experience requires explicit target-health state "
                    "for healing critical chance",
                ),
            )
        target_health_fraction = float(target_health_fraction)
        if not 0.0 <= target_health_fraction <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")

        missing_health_fraction = 1.0 - target_health_fraction
        return ExtremeNecromancerNearDeathExperienceResult(
            critical_chance_bonus=(
                self.MAX_HEALING_CRITICAL_CHANCE_BONUS * missing_health_fraction
            ),
            living_death_slotted=True,
            unresolved=(),
        )
