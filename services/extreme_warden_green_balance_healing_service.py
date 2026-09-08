from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from minmax.warden_passive_input_resolver import WardenPassiveInputResolver
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeWardenGreenBalanceHealingResult:
    multiplier: float
    green_balance_slots: int
    unresolved: tuple[str, ...]


class ExtremeWardenGreenBalanceHealingService:
    """Resolve reviewed Emerald Moss ability-family healing for Extreme builds.

    Emerald Moss is not generic sheet Healing Done. At reviewed max rank it
    increases healing done by Green Balance abilities by 5% for each Green
    Balance ability slotted on the active bar. The effect therefore belongs at
    the healing-event family layer, after the canonical sheet pipeline has built
    the underlying heal value.

    Explicit class-line materialization remains authoritative. A pure Warden has
    Green Balance implicitly; subclass snapshots must explicitly carry the line.
    Missing passive-rank or slot-line evidence returns a lower-bound multiplier
    plus blockers rather than silently assigning unknown mechanics zero value.
    """

    PASSIVE_NAME = "Emerald Moss"
    GREEN_BALANCE = "green balance"
    HEALING_PER_SLOTTED_ABILITY = 0.05

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

    def resolve(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        ability_name: str,
        active_bar: str = "front",
    ) -> ExtremeWardenGreenBalanceHealingResult:
        ability_line = self.skill_line_repository.skill_line_for_ability_name(
            str(ability_name or "").strip()
        )
        if str(ability_line or "").strip().casefold() != self.GREEN_BALANCE:
            return ExtremeWardenGreenBalanceHealingResult(1.0, 0, ())

        equipped = WardenPassiveInputResolver.equipped_warden_line_ids(build)
        if WardenPassiveInputResolver.GREEN_BALANCE_ID not in equipped:
            return ExtremeWardenGreenBalanceHealingResult(1.0, 0, ())

        passive_ranks = progression.passive_ranks
        if passive_ranks is None:
            return ExtremeWardenGreenBalanceHealingResult(
                1.0,
                0,
                ("Emerald Moss passive rank is not recorded",),
            )
        rank = progression.passive_rank(self.PASSIVE_NAME)
        if rank is None:
            return ExtremeWardenGreenBalanceHealingResult(
                1.0,
                0,
                ("Passive rank is not recorded for character: Emerald Moss",),
            )
        if rank == 0:
            return ExtremeWardenGreenBalanceHealingResult(1.0, 0, ())

        maximum = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if maximum is None:
            return ExtremeWardenGreenBalanceHealingResult(
                1.0,
                0,
                ("Passive max rank is not available in canonical data: Emerald Moss",),
            )
        if rank != maximum:
            return ExtremeWardenGreenBalanceHealingResult(
                1.0,
                0,
                (f"Partial passive rank is not yet modeled: Emerald Moss {rank}/{maximum}",),
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
                    "Emerald Moss slot count: could not resolve canonical skill line "
                    f"for slotted ability {name!r} on {active_bar} bar"
                )
                continue
            if str(skill_line).strip().casefold() == self.GREEN_BALANCE:
                count += 1

        multiplier = 1.0 + self.HEALING_PER_SLOTTED_ABILITY * count
        return ExtremeWardenGreenBalanceHealingResult(
            multiplier=multiplier,
            green_balance_slots=count,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
