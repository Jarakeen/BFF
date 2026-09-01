from __future__ import annotations

import re
from dataclasses import dataclass

from models.build_model import PlayerBuild

from .character_build.champion_points import ChampionPointAllocation


_NON_ID = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SavedChampionPointSlotAdaptation:
    """Canonical allocations recovered from the saved build's CP slot grid.

    ``PlayerBuild.ChampionPoints`` is populated by the build editor's twelve
    Champion Point slot widgets (four per discipline). Entries here therefore
    represent slotted selections, not the character's entire purchased CP tree.
    """

    allocations: tuple[ChampionPointAllocation, ...] = ()
    unresolved: tuple[str, ...] = ()


def _node_id(name: str) -> str:
    normalized = _NON_ID.sub("_", str(name or "").strip().casefold()).strip("_")
    return normalized


def adapt_saved_champion_point_slots(
    build: PlayerBuild,
) -> SavedChampionPointSlotAdaptation:
    allocations: list[ChampionPointAllocation] = []
    unresolved: list[str] = []

    for index, entry in enumerate(build.ChampionPoints, start=1):
        name = str(entry.Name or "").strip()
        points_text = str(entry.Points or "").strip()
        if not name and not points_text:
            continue
        if not name:
            unresolved.append(
                f"Saved Champion Point slot {index} has points but no node name"
            )
            continue

        try:
            points = int(points_text or 0)
        except (TypeError, ValueError):
            unresolved.append(
                f"Saved Champion Point slot {index} has invalid points: {name}: {points_text!r}"
            )
            continue
        if points < 0:
            unresolved.append(
                f"Saved Champion Point slot {index} has negative points: {name}: {points}"
            )
            continue

        node_id = _node_id(name)
        if not node_id:
            unresolved.append(
                f"Saved Champion Point slot {index} has no canonical node identity: {name!r}"
            )
            continue
        allocations.append(ChampionPointAllocation(node_id=node_id, points=points))

    return SavedChampionPointSlotAdaptation(
        allocations=tuple(allocations),
        unresolved=tuple(unresolved),
    )
