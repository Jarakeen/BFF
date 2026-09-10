from __future__ import annotations

from dataclasses import dataclass


IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeDragonknightEarthenHeartPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeDragonknightEarthenHeartPassiveReview:
    """Live-U50 Earthen Heart passive review for MOST Actual Heal.

    The U49 Dragonknight refresh replaced the older Earthen Heart passive roster.
    The current four passives affect Armor, damage, Ultimate/Critical Damage, and
    fully charged Heavy Attack/Stamina behavior. None enlarge the numeric
    magnitude of one healing event.

    Obsidian Shield-family Major Mending remains a valid current active-skill
    effect and is modeled separately by ExtremeDragonknightEarthenHeartMendingService;
    it must not be confused with the passive-family review.
    """

    PASSIVE_NAMES = (
        "Heart of Stone",
        "Landslide",
        "Blessing at the Peak",
        "Mountain Giant",
    )

    _ENTRIES = (
        ExtremeDragonknightEarthenHeartPassiveReviewEntry(
            "Heart of Stone",
            False,
            IRRELEVANT,
            "Live-U50 Earthen Heart passive review",
            "Increases Armor rather than healing-event magnitude.",
        ),
        ExtremeDragonknightEarthenHeartPassiveReviewEntry(
            "Landslide",
            False,
            IRRELEVANT,
            "Live-U50 Earthen Heart passive review",
            "Builds damage-done stacks from dealing damage; it does not increase healing-event magnitude.",
        ),
        ExtremeDragonknightEarthenHeartPassiveReviewEntry(
            "Blessing at the Peak",
            False,
            IRRELEVANT,
            "Live-U50 Earthen Heart passive review",
            "Generates Ultimate and increases Critical Damage, not Critical Healing.",
        ),
        ExtremeDragonknightEarthenHeartPassiveReviewEntry(
            "Mountain Giant",
            False,
            IRRELEVANT,
            "Live-U50 Earthen Heart passive review",
            "With an Earthen Heart ability slotted, fully charged Heavy Attacks apply Off Balance and restore Stamina; this does not enlarge one healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeDragonknightEarthenHeartPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Earthen Heart passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Earthen Heart passive review contains duplicate passives")
        if any(row.objective_relevant for row in rows):
            raise ValueError("Earthen Heart passives must remain irrelevant to MOST Actual Heal")
        if any(row.coverage_status != IRRELEVANT for row in rows):
            raise ValueError("Objective-irrelevant Earthen Heart passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return True
