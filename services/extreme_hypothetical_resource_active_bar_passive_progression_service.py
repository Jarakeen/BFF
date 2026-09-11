from __future__ import annotations

"""Grant reviewed shared-line passives required by Extreme resource bar search.

This decorator supplies progression evidence only. Resource math remains in the
shared Nightblade/Guild passive resolvers. Nightblade class-passive ranks are
already supplied by the hypothetical class progression for routes that equip the
relevant class line; this layer only needs to add Mages Guild + Magicka Controller
for ``max_magicka``.
"""

from dataclasses import replace
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_hypothetical_resource_armor_passive_progression_service import (
    ExtremeHypotheticalResourceArmorPassiveProgressionService,
)


class ExtremeHypotheticalResourceActiveBarPassiveProgressionService:
    """Decorate resource progression with reviewed active-bar passive ownership."""

    PASSIVE_NAME = "Magicka Controller"
    SKILL_LINE = "Mages Guild"
    SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        objective_key: str,
        progression_service: ExtremeHypotheticalResourceArmorPassiveProgressionService | None = None,
        skill_line_repository: SkillLineRepository | None = None,
    ) -> None:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource active-bar passive objective: {objective_key!r}")
        if database_path is None and (
            progression_service is None or skill_line_repository is None
        ):
            raise ValueError(
                "database_path is required unless both progression and skill-line services are supplied"
            )
        self.objective_key = key
        self.database_path = Path(database_path) if database_path is not None else None
        self.progression_service = progression_service or ExtremeHypotheticalResourceArmorPassiveProgressionService(
            self.database_path,  # type: ignore[arg-type]
            objective_key=key,
        )
        self.skill_line_repository = skill_line_repository or SkillLineRepository(
            self.database_path  # type: ignore[arg-type]
        )

    def canonical_max_rank(self) -> int:
        rank = self.skill_line_repository.passive_max_rank(self.PASSIVE_NAME)
        if rank is None or int(rank) <= 0:
            raise ValueError(
                "Canonical max rank is unavailable for Extreme passive: Magicka Controller"
            )
        return int(rank)

    def normalize(
        self,
        progression: CharacterProgression,
        route: ExtremeHealClassRoute,
    ) -> CharacterProgression:
        candidate = self.progression_service.normalize(progression, route)
        if self.objective_key != "max_magicka":
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
