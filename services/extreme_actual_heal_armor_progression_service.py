from __future__ import annotations

"""Grant reviewed non-class armor passives to hypothetical standing H1 routes.

Extreme class-route search already normalizes the selected class lines to legal
maximum progression. Standing MOST Actual Heal also searches armor composition,
so its theoretical character must not depend on whether the saved seed character
happened to purchase the non-class passives that make those armor states matter.

Only passives with reviewed H1 magnitude consequences are added here:

* Medium Armor: Agility -> Weapon/Spell Damage percentage;
* Medium Armor: Dexterity -> Critical Healing;
* Undaunted: Undaunted Mettle -> Max Health/Magicka/Stamina by armor-type count.

All math remains owned by the canonical armor/Undaunted input resolvers. This
service changes legal progression evidence only.
"""

from dataclasses import replace
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.skill_line_repository import SkillLineRepository
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_resource_canonical_static_snapshot_service import (
    ExtremeResourceCanonicalStaticSnapshotService,
)


class ExtremeActualHealArmorProgressionService:
    """Decorate hypothetical H1 class routes with reviewed max-rank armor passives."""

    PASSIVES = (
        ("Medium Armor", "Agility"),
        ("Medium Armor", "Dexterity"),
        ("Undaunted", "Undaunted Mettle"),
    )

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
                "database_path is required unless both class progression and skill repository are supplied"
            )
        self.database_path = Path(database_path) if database_path is not None else None
        self.class_progression_service = class_progression_service or (
            ExtremeHypotheticalClassProgressionService(self.database_path)  # type: ignore[arg-type]
        )
        if skill_line_repository is None and self.database_path is not None:
            skill_line_repository = ExtremeResourceCanonicalStaticSnapshotService(
                self.database_path
            ).build().skill_line_repository
        self.skill_line_repository = skill_line_repository  # type: ignore[assignment]

    def _max_rank(self, passive_name: str) -> int:
        rank = self.skill_line_repository.passive_max_rank(passive_name)
        if rank is None or int(rank) <= 0:
            raise ValueError(
                f"Canonical max rank is unavailable for Extreme H1 passive: {passive_name}"
            )
        return int(rank)

    def normalize(
        self,
        progression: CharacterProgression,
        route: ExtremeHealClassRoute,
    ) -> CharacterProgression:
        candidate = self.class_progression_service.normalize(progression, route)
        owned_lines = list(candidate.owned_skill_lines)
        passive_ranks = dict(candidate.passive_ranks or {})

        for skill_line, passive_name in self.PASSIVES:
            if skill_line not in owned_lines:
                owned_lines.append(skill_line)
            passive_ranks = {
                name: value
                for name, value in passive_ranks.items()
                if str(name).strip().casefold() != passive_name.casefold()
            }
            passive_ranks[passive_name] = self._max_rank(passive_name)

        return replace(
            candidate,
            owned_skill_lines=tuple(owned_lines),
            passive_ranks=passive_ranks,
        )


__all__ = ["ExtremeActualHealArmorProgressionService"]
