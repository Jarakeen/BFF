from __future__ import annotations

from dataclasses import dataclass


IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeWardenWintersEmbracePassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeWardenWintersEmbracePassiveReview:
    """Exhaustive live-U50 Winter's Embrace review for MOST Actual Heal.

    None of the four passives increases the numeric magnitude of a healing event.
    Frozen Armor is already modeled in the shared Warden passive resolver because
    it matters to resistance-focused Extreme objectives; that existing support is
    deliberately not misclassified as healing relevance here.
    """

    PASSIVE_NAMES = (
        "Glacial Presence",
        "Frozen Armor",
        "Icy Aura",
        "Piercing Cold",
    )

    _ENTRIES = (
        ExtremeWardenWintersEmbracePassiveReviewEntry(
            "Glacial Presence",
            False,
            IRRELEVANT,
            "Live-U50 Winter's Embrace passive review",
            "Changes Chilled application/damage rather than healing-event magnitude.",
        ),
        ExtremeWardenWintersEmbracePassiveReviewEntry(
            "Frozen Armor",
            False,
            IRRELEVANT,
            "WardenPassiveInputResolver",
            "Adds Physical and Spell Resistance per slotted Winter's Embrace ability; it is modeled for defensive objectives but does not enlarge MOST Actual Heal.",
        ),
        ExtremeWardenWintersEmbracePassiveReviewEntry(
            "Icy Aura",
            False,
            IRRELEVANT,
            "Live-U50 Winter's Embrace passive review",
            "Applies Bite of Winter/Major Maim from qualifying incoming melee damage and changes enemy damage output, not healing-event magnitude.",
        ),
        ExtremeWardenWintersEmbracePassiveReviewEntry(
            "Piercing Cold",
            False,
            IRRELEVANT,
            "Live-U50 Winter's Embrace passive review",
            "Increases amount blocked and Frost Damage rather than healing-event magnitude.",
        ),
    )

    def items(self) -> tuple[ExtremeWardenWintersEmbracePassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Winter's Embrace passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Winter's Embrace passive review contains duplicate passives")
        for row in rows:
            if row.objective_relevant or row.coverage_status != IRRELEVANT:
                raise ValueError(
                    f"Winter's Embrace healing review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status == IRRELEVANT for row in rows
        )
