from __future__ import annotations

"""Grant reviewed resource-relevant armor passives to hypothetical Extreme builds.

This decorator owns progression evidence only. Shared armor-passive math remains in
``ArmorPassiveInputResolver`` and ``passive_math``. The current reviewed resource
subset contains Heavy Armor's max-rank Juggernaut for ``max_health``; Magicka and
Stamina pass through unchanged.
"""

from dataclasses import replace
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_hypothetical_undaunted_progression_service import (
    ExtremeHypotheticalUndauntedProgressionService,
)


class ExtremeHypotheticalResourceArmorPassiveProgressionService:
    """Decorate reviewed Extreme resource progression with canonical Juggernaut."""

    PASSIVE_NAME = "Juggernaut"
    SKILL_LINE = "Heavy Armor"
    SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        objective_key: str,
        progression_service: ExtremeHypotheticalUndauntedProgressionService | None = None,
        skill_line_repository: SkillLineRepository | None = None,
    ) -> None:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource armor-passive objective: {objective_key!r}")
        if database_path is None and (
            progression_service is None or skill_line_repository is None
        ):
            raise ValueError(
                "database_path is required unless both progression and skill-line services are supplied"
            )
        self.objective_key = key
        self.database_path = Path(database_path) if database_path is not None else None
        self.progression_service = progression_service or ExtremeHypotheticalUndauntedProgressionService(
            self.database_path  # type: ignore[arg-type]
        )
        self.skill_line_repository = skill_line_repository or SkillLineRepository(
            self.database_path  # type: ignore[arg-type]
        )

    def canonical_max_rank(self) -> int:
        rank = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if rank is None or int(rank) <= 0:
            raise ValueError(
                "Canonical max rank is unavailable for Extreme passive: Juggernaut"
            )
        return int(rank)

    def normalize(
        self,
        progression: CharacterProgression,
        route: ExtremeHealClassRoute,
    ) -> CharacterProgression:
        candidate = self.progression_service.normalize(progression, route)
        if self.objective_key != "max_health":
            return candidate

        rank = self.canonical_max_rank()
        owned_lines = tuple(dict.fromkeys((*candidate.owned_skill_lines, self.SKILL_LINE)))
        passive_ranks = {
            name: value
            for name, value in dict(candidate.passive_ranks or {}).items()
            if str(name).strip().casefold() != self.PASSIVE_NAME.casefold()
        }
        passive_ranks[self.PASSIVE_NAME] = rank
        return replace(
            candidate,
            owned_skill_lines=owned_lines,
            passive_ranks=passive_ranks,
        )
