from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"
INTEGRATION_PENDING = "integration_pending"


@dataclass(frozen=True)
class ExtremeSorcererDaedricSummoningPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeSorcererDaedricSummoningPassiveReview:
    """Live-U50 Daedric Summoning review for MOST Actual Heal.

    Expert Summoner has two relevant resource branches. Its standing 5% Max
    Magicka/Stamina contribution is already canonical. The separate 5% Max
    Health branch requires an explicitly active permanent pet and is not yet
    represented in the shared context, so this family must remain incomplete.
    """

    PASSIVE_NAMES = (
        "Rebate",
        "Power Stone",
        "Daedric Protection",
        "Expert Summoner",
    )

    _ENTRIES = (
        ExtremeSorcererDaedricSummoningPassiveReviewEntry(
            "Rebate",
            False,
            IRRELEVANT,
            "Live-U50 Daedric Summoning passive review",
            "Restores Magicka when a summoned non-Ultimate Daedric Summoning pet ends; sustain does not enlarge one healing event.",
        ),
        ExtremeSorcererDaedricSummoningPassiveReviewEntry(
            "Power Stone",
            False,
            IRRELEVANT,
            "Live-U50 Daedric Summoning passive review",
            "Reduces Ultimate cost rather than healing-event magnitude.",
        ),
        ExtremeSorcererDaedricSummoningPassiveReviewEntry(
            "Daedric Protection",
            False,
            IRRELEVANT,
            "Live-U50 Daedric Summoning passive review",
            "Changes Health/Stamina Recovery while a Daedric Summoning ability is slotted; recovery does not enlarge one healing event.",
        ),
        ExtremeSorcererDaedricSummoningPassiveReviewEntry(
            "Expert Summoner",
            True,
            INTEGRATION_PENDING,
            "SorcererPassiveInputResolver + BuildCalculationContextFactory",
            "Standing 5% Max Magicka and Max Stamina is implemented. The separate 5% Max Health branch requires proof that a permanent pet is active and still needs explicit runtime/context wiring before health-scaled heals can be exact.",
        ),
    )

    def items(self) -> tuple[ExtremeSorcererDaedricSummoningPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Daedric Summoning passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Daedric Summoning passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if len(relevant) != 1 or relevant[0].passive_name != "Expert Summoner":
            raise ValueError(
                "Daedric Summoning healing review must identify only Expert Summoner as objective-relevant"
            )
        if relevant[0].coverage_status != INTEGRATION_PENDING:
            raise ValueError(
                "Expert Summoner must remain integration_pending until the permanent-pet Max Health branch is wired"
            )
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Daedric Summoning passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return False
