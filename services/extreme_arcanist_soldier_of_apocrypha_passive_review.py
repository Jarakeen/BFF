from __future__ import annotations

from dataclasses import dataclass


IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeArcanistSoldierPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeArcanistSoldierOfApocryphaPassiveReview:
    """Live-U50 Soldier of Apocrypha review for MOST Actual Heal."""

    PASSIVE_NAMES = (
        "Aegis of the Unseen",
        "Wellspring of the Abyss",
        "Circumvented Fate",
        "Implacable Outcome",
    )

    _ENTRIES = (
        ExtremeArcanistSoldierPassiveReviewEntry(
            "Aegis of the Unseen",
            False,
            IRRELEVANT,
            "Live-U50 Soldier of Apocrypha passive review",
            "Adds Armor while a beneficial Soldier of Apocrypha ability is active; Armor does not enlarge one healing event.",
        ),
        ExtremeArcanistSoldierPassiveReviewEntry(
            "Wellspring of the Abyss",
            False,
            IRRELEVANT,
            "Live-U50 Soldier of Apocrypha passive review",
            "Adds Health, Magicka, and Stamina Recovery per Soldier ability slotted; recovery is sustain rather than healing-event magnitude.",
        ),
        ExtremeArcanistSoldierPassiveReviewEntry(
            "Circumvented Fate",
            False,
            IRRELEVANT,
            "Live-U50 Soldier of Apocrypha passive review",
            "Grants Minor Evasion after casting an Arcanist ability; area-damage mitigation does not enlarge a heal.",
        ),
        ExtremeArcanistSoldierPassiveReviewEntry(
            "Implacable Outcome",
            False,
            IRRELEVANT,
            "Live-U50 Soldier of Apocrypha passive review",
            "Grants Ultimate when Crux is consumed; Ultimate economy does not enlarge one healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeArcanistSoldierPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Soldier of Apocrypha passive review must exactly match the reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Soldier of Apocrypha passive review contains duplicate passives")
        if any(row.objective_relevant for row in rows):
            raise ValueError(
                "Soldier of Apocrypha passives must remain objective-irrelevant for MOST Actual Heal"
            )
        if any(row.coverage_status != IRRELEVANT for row in rows):
            raise ValueError("Soldier of Apocrypha passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return True
