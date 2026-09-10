from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


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
    Magicka/Stamina contribution is canonical through ``SorcererPassiveInputResolver``.
    Its separate 5% Max Health branch is now modeled through an explicit permanent-
    pet conditional context rebuild before healing coefficient evaluation.
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
            "Restores Magicka or Stamina when a non-Ultimate Daedric Summoning ability ends; sustain does not enlarge one healing event.",
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
            "Reduces damage taken while a Daedric Summoning ability is active; mitigation does not enlarge one healing event.",
        ),
        ExtremeSorcererDaedricSummoningPassiveReviewEntry(
            "Expert Summoner",
            True,
            IMPLEMENTED,
            "SorcererPassiveInputResolver + ExtremeSorcererExpertSummonerPetContextService + ExtremeSorcererConditionalActualHealService",
            "Standing 5% Max Magicka and Max Stamina is canonical. The separate 5% Max Health branch is applied only when the caller explicitly proves a permanent pet is active, and the additive Health percentage is inserted before canonical resource rounding and healing coefficient evaluation.",
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
        if relevant[0].coverage_status != IMPLEMENTED:
            raise ValueError("Expert Summoner must remain implemented")
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Daedric Summoning passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT}
            for row in rows
        )
