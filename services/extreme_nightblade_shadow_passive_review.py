from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"
INTEGRATION_PENDING = "integration_pending"


@dataclass(frozen=True)
class ExtremeNightbladeShadowPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeNightbladeShadowPassiveReview:
    """Exhaustive live-U50 Shadow review for MOST Actual Heal.

    Dark Vigor is the only Shadow passive that can change the numeric magnitude
    of an Extreme healing event. At max rank it grants 5% Max Health for each
    Shadow ability slotted on the active bar. That resource increase can enlarge
    any legal Max-Health-scaled heal, including subclassed combinations, so the
    passive belongs in the shared canonical stat pipeline rather than in a
    Nightblade-heal-only multiplier.

    ``NightbladePassiveInputResolver`` already owns the verified active-bar slot
    counting and Max Health percentage contribution. Production context-factory
    progression wiring remains the final integration step, so the family fails
    closed as incomplete until that bridge is present.
    """

    PASSIVE_NAMES = (
        "Refreshing Shadows",
        "Shadow Barrier",
        "Dark Vigor",
        "Dark Veil",
    )

    _ENTRIES = (
        ExtremeNightbladeShadowPassiveReviewEntry(
            "Refreshing Shadows",
            False,
            IRRELEVANT,
            "Live-U50 Shadow passive review",
            "Changes Health, Magicka, and Stamina Recovery rather than one healing-event magnitude.",
        ),
        ExtremeNightbladeShadowPassiveReviewEntry(
            "Shadow Barrier",
            False,
            IRRELEVANT,
            "Live-U50 Shadow passive review",
            "Grants Major Resolve after casting a Shadow ability; this is defensive resistance state, not healing-event magnitude.",
        ),
        ExtremeNightbladeShadowPassiveReviewEntry(
            "Dark Vigor",
            True,
            INTEGRATION_PENDING,
            "NightbladePassiveInputResolver",
            "Verified max-rank math grants 5% Max Health per Shadow ability slotted on the active bar. Resolver support exists, but BuildCalculationContextFactory must still request explicit Dark Vigor ownership from character progression before this family can be counted complete.",
        ),
        ExtremeNightbladeShadowPassiveReviewEntry(
            "Dark Veil",
            False,
            IRRELEVANT,
            "Live-U50 Shadow passive review",
            "Extends Shadow ability duration and therefore changes uptime/cadence, not the numeric magnitude of one healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeNightbladeShadowPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Shadow passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Shadow passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if len(relevant) != 1 or relevant[0].passive_name != "Dark Vigor":
            raise ValueError("Shadow healing review must identify only Dark Vigor as objective-relevant")
        if relevant[0].coverage_status != INTEGRATION_PENDING:
            raise ValueError("Dark Vigor must remain integration_pending until canonical context wiring exists")
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Shadow passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return False
