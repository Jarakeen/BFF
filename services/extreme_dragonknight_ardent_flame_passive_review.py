from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"
INTEGRATION_PENDING = "integration_pending"


@dataclass(frozen=True)
class ExtremeDragonknightArdentFlamePassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeDragonknightArdentFlamePassiveReview:
    """Live-U50 Ardent Flame review for MOST Actual Heal.

    A Soul Ablaze is the only Ardent Flame passive that can enlarge the numeric
    amount received by a Dragonknight self-heal. Rank 1 grants 4% Healing Taken
    and rank 2 grants 8%. The canonical resolver exists, but production context
    wiring remains pending, so this family intentionally stays incomplete.
    """

    PASSIVE_NAMES = (
        "Combustion",
        "Traumatic Burns",
        "Fan the Flames",
        "A Soul Ablaze",
    )

    _ENTRIES = (
        ExtremeDragonknightArdentFlamePassiveReviewEntry(
            "Combustion",
            False,
            IRRELEVANT,
            "Live-U50 Ardent Flame passive review",
            "Restores Magicka and Stamina when Burning is applied; sustain does not enlarge one healing event.",
        ),
        ExtremeDragonknightArdentFlamePassiveReviewEntry(
            "Traumatic Burns",
            False,
            IRRELEVANT,
            "Live-U50 Ardent Flame passive review",
            "Changes enemy Flame Damage Taken and movement speed after Ardent Flame direct damage; it does not increase healing-event magnitude.",
        ),
        ExtremeDragonknightArdentFlamePassiveReviewEntry(
            "Fan the Flames",
            False,
            IRRELEVANT,
            "Live-U50 Ardent Flame passive review",
            "Changes Burning application chance and Burning damage; it does not increase healing-event magnitude.",
        ),
        ExtremeDragonknightArdentFlamePassiveReviewEntry(
            "A Soul Ablaze",
            True,
            INTEGRATION_PENDING,
            "DragonknightPassiveInputResolver",
            "Rank-aware 4%/8% Healing Taken contribution is implemented in the canonical Dragonknight resolver, but BuildCalculationContextFactory must still request passive ownership/rank before production self-heal evaluation is exact.",
        ),
    )

    def items(self) -> tuple[ExtremeDragonknightArdentFlamePassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Ardent Flame passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Ardent Flame passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if len(relevant) != 1 or relevant[0].passive_name != "A Soul Ablaze":
            raise ValueError(
                "Ardent Flame healing review must identify only A Soul Ablaze as objective-relevant"
            )
        if relevant[0].coverage_status != INTEGRATION_PENDING:
            raise ValueError(
                "A Soul Ablaze must remain integration_pending until canonical context wiring exists"
            )
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Ardent Flame passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return False
