from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeArcanistHeraldPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeArcanistHeraldOfTheTomePassiveReview:
    """Live-U50 Herald of the Tome review for MOST Actual Heal."""

    PASSIVE_NAMES = (
        "Fated Fortune",
        "Harnessed Quintessence",
        "Psychic Lesion",
        "Splintered Secrets",
    )

    _ENTRIES = (
        ExtremeArcanistHeraldPassiveReviewEntry(
            "Fated Fortune",
            True,
            IMPLEMENTED,
            "ExtremeArcanistFatedFortuneCriticalHealingService + ExtremeArcanistConditionalActualHealService",
            "Generating or consuming Crux can open a reviewed seven-second window that adds 12% Critical Healing; the bonus is applied to canonical Critical Healing before event critical magnitude is calculated.",
        ),
        ExtremeArcanistHeraldPassiveReviewEntry(
            "Harnessed Quintessence",
            True,
            IMPLEMENTED,
            "ExtremeArcanistHarnessedQuintessenceService + ExtremeArcanistHarnessedQuintessenceContextService + ExtremeArcanistConditionalActualHealService",
            "Restoring Magicka or Stamina can open a reviewed ten-second rank-aware flat Weapon/Spell Damage window: 142 at rank 1 and 284 at rank 2. The flat power is inserted before canonical percentage modifiers and before healing coefficient evaluation.",
        ),
        ExtremeArcanistHeraldPassiveReviewEntry(
            "Psychic Lesion",
            False,
            IRRELEVANT,
            "Live-U50 Herald of the Tome passive review",
            "Increases Status Effect damage and Status Effect Chance while a Herald ability is slotted; it does not enlarge healing-event magnitude.",
        ),
        ExtremeArcanistHeraldPassiveReviewEntry(
            "Splintered Secrets",
            False,
            IRRELEVANT,
            "Live-U50 Herald of the Tome passive review",
            "Adds Physical and Spell Penetration per Herald ability slotted; penetration does not enlarge a healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeArcanistHeraldPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Herald of the Tome passive review must exactly match the reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Herald of the Tome passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if tuple(row.passive_name for row in relevant) != (
            "Fated Fortune",
            "Harnessed Quintessence",
        ):
            raise ValueError(
                "Herald healing review must identify Fated Fortune and Harnessed Quintessence as objective-relevant"
            )
        if any(row.coverage_status != IMPLEMENTED for row in relevant):
            raise ValueError("Relevant Herald passives must remain implemented")
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Herald passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return True
