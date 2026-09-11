from __future__ import annotations

"""Grant reviewed max-rank Undaunted Mettle to hypothetical Extreme builds.

Extreme's structural class progression deliberately owns only selected class lines.
This decorator adds the one reviewed non-class passive currently needed by the
max-resource armor continuation: Undaunted Mettle.  It resolves the canonical max
rank through ``SkillLineRepository`` and changes progression evidence only; all
resource math remains owned by the shared ``UndauntedPassiveInputResolver``.
"""

from dataclasses import replace
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)


class ExtremeHypotheticalUndauntedProgressionService:
    """Decorate hypothetical class progression with proven max-rank Mettle."""

    PASSIVE_NAME = "Undaunted Mettle"
    SKILL_LINE = "Undaunted"

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        class_progression_service: ExtremeHypotheticalClassProgressionService | None = None,
        skill_line_repository: SkillLineRepository | None = None,
    ) -> None:
        if database_path is None and (
            class_progression_service is None or skill_line_repository is None
        ):
            raise ValueError(
                "database_path is required unless both progression and skill-line services are supplied"
            )
        self.database_path = Path(database_path) if database_path is not None else None
        self.class_progression_service = class_progression_service or (
            ExtremeHypotheticalClassProgressionService(self.database_path)  # type: ignore[arg-type]
        )
        self.skill_line_repository = skill_line_repository or SkillLineRepository(
            self.database_path  # type: ignore[arg-type]
        )

    def canonical_max_rank(self) -> int:
        rank = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if rank is None or int(rank) <= 0:
            raise ValueError(
                "Canonical max rank is unavailable for Extreme passive: Undaunted Mettle"
            )
        return int(rank)

    def normalize(
        self,
        progression: CharacterProgression,
        route: ExtremeHealClassRoute,
    ) -> CharacterProgression:
        candidate = self.class_progression_service.normalize(progression, route)
        rank = self.canonical_max_rank()

        owned_lines = tuple(
            dict.fromkeys((*candidate.owned_skill_lines, self.SKILL_LINE))
        )
        passive_ranks = dict(candidate.passive_ranks or {})
        # Remove any differently-cased duplicate before installing canonical spelling.
        passive_ranks = {
            name: value
            for name, value in passive_ranks.items()
            if str(name).strip().casefold() != self.PASSIVE_NAME.casefold()
        }
        passive_ranks[self.PASSIVE_NAME] = rank
        return replace(
            candidate,
            owned_skill_lines=owned_lines,
            passive_ranks=passive_ranks,
        )
