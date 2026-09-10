from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeSorcererStormCallingPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeSorcererStormCallingPassiveReview:
    """Exhaustive live-U50 Storm Calling review for MOST Actual Heal."""

    PASSIVE_NAMES = (
        "Capacitor",
        "Energized",
        "Amplitude",
        "Expert Mage",
    )

    _ENTRIES = (
        ExtremeSorcererStormCallingPassiveReviewEntry(
            "Capacitor",
            False,
            IRRELEVANT,
            "Live-U50 Storm Calling passive review",
            "Changes Magicka Recovery rather than the magnitude of one healing event.",
        ),
        ExtremeSorcererStormCallingPassiveReviewEntry(
            "Energized",
            False,
            IRRELEVANT,
            "Live-U50 Storm Calling passive review",
            "Changes Shock/Physical damage rather than healing-event magnitude.",
        ),
        ExtremeSorcererStormCallingPassiveReviewEntry(
            "Amplitude",
            False,
            IRRELEVANT,
            "Live-U50 Storm Calling passive review",
            "Changes damage against high-Health targets rather than healing-event magnitude.",
        ),
        ExtremeSorcererStormCallingPassiveReviewEntry(
            "Expert Mage",
            True,
            IMPLEMENTED,
            "SorcererPassiveInputResolver + BuildCalculationContextFactory",
            "At max rank grants 108 Weapon and Spell Damage per Sorcerer ability slotted on the active bar; canonical power inputs therefore enlarge any legal power-scaled heal.",
        ),
    )

    def items(self) -> tuple[ExtremeSorcererStormCallingPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Storm Calling passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Storm Calling passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if len(relevant) != 1 or relevant[0].passive_name != "Expert Mage":
            raise ValueError(
                "Storm Calling healing review must identify only Expert Mage as objective-relevant"
            )
        if relevant[0].coverage_status != IMPLEMENTED:
            raise ValueError("Expert Mage must remain implemented")
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Storm Calling passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES)
