from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.skill_line_repository import SkillLineRepository
from models.build_model import PlayerBuild
from services.extreme_necromancer_living_death_healing_service import (
    ExtremeNecromancerLivingDeathHealingService,
)


@dataclass(frozen=True)
class ExtremeNecromancerLivingDeathSlottedHealingResult:
    multiplier: float
    qualifying_skill: str | None
    unresolved: tuple[str, ...]


class ExtremeNecromancerLivingDeathSlottedHealingService:
    """Resolve the reviewed Restoring Tether-family while-slotted heal bonus.

    Current reviewed Living Death skill text gives Restoring Tether and its two
    morphs, Braided Tether and Mortal Coil, 3% generic Healing Done while that
    skill is slotted. These are one base-skill family, so a legal character may
    receive this contribution once, not once per morph name.

    The effect is active-bar-only and generic: it can increase a heal from a
    different skill line. Explicit ``ClassSkillLines`` remain authoritative for
    subclass snapshots so an illegally retained Living Death skill cannot become
    free Healing Done after that class line has been removed.
    """

    LIVING_DEATH_ID = "living_death"
    HEALING_DONE_MULTIPLIER = 1.03
    QUALIFYING_SKILLS = frozenset(
        {"restoring tether", "braided tether", "mortal coil"}
    )

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
        active_bar: str = "front",
    ) -> ExtremeNecromancerLivingDeathSlottedHealingResult:
        skills = (
            build.BackBarSkills
            if str(active_bar or "front").casefold() == "back"
            else build.FrontBarSkills
        )
        qualifying_names = [
            str(raw_name or "").strip()
            for raw_name in skills
            if str(raw_name or "").strip().casefold() in self.QUALIFYING_SKILLS
        ]
        if not qualifying_names:
            return ExtremeNecromancerLivingDeathSlottedHealingResult(1.0, None, ())

        if not self.living_death_equipped(build):
            return ExtremeNecromancerLivingDeathSlottedHealingResult(
                1.0,
                None,
                (
                    "Living Death slotted Healing Done: qualifying skill is present "
                    "but Living Death is not equipped in the class route",
                ),
            )

        resolved: list[str] = []
        unresolved: list[str] = []
        for name in qualifying_names:
            skill_line = self.skill_line_repository.skill_line_for_ability_name(name)
            if skill_line is None:
                unresolved.append(
                    "Living Death slotted Healing Done: could not resolve canonical "
                    f"skill line for slotted ability {name!r} on {active_bar} bar"
                )
                continue
            if self._line_id(skill_line) != self.LIVING_DEATH_ID:
                unresolved.append(
                    "Living Death slotted Healing Done: canonical skill line for "
                    f"{name!r} is {skill_line!r}, not Living Death"
                )
                continue
            resolved.append(name)

        if len(resolved) > 1:
            unresolved.append(
                "Living Death slotted Healing Done: multiple Restoring Tether-family "
                "skills are slotted; legal morph/base duplication is unresolved"
            )

        qualifying_skill = resolved[0] if resolved else None
        multiplier = self.HEALING_DONE_MULTIPLIER if qualifying_skill else 1.0
        return ExtremeNecromancerLivingDeathSlottedHealingResult(
            multiplier=multiplier,
            qualifying_skill=qualifying_skill,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
