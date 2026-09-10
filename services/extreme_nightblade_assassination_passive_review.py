from __future__ import annotations

from dataclasses import dataclass


IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeNightbladeAssassinationPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeNightbladeAssassinationPassiveReview:
    """Exhaustive live-U50 Assassination review for MOST Actual Heal.

    None of the four passives increases the numeric magnitude of a critical heal.
    Critical-chance effects remain relevant to expected-value or proc-frequency
    objectives, but MOST Actual Heal scores the magnitude of a proven critical
    healing event rather than the probability of producing one.
    """

    PASSIVE_NAMES = (
        "Master Assassin",
        "Executioner",
        "Pressure Points",
        "Hemorrhage",
    )

    _ENTRIES = (
        ExtremeNightbladeAssassinationPassiveReviewEntry(
            "Master Assassin",
            False,
            IRRELEVANT,
            "Live-U50 Assassination passive review",
            "Increases Critical Chance against flanked enemies; it changes critical-event probability, not critical-heal magnitude.",
        ),
        ExtremeNightbladeAssassinationPassiveReviewEntry(
            "Executioner",
            False,
            IRRELEVANT,
            "Live-U50 Assassination passive review",
            "Restores Magicka and Stamina after a recently damaged enemy dies; it is sustain rather than healing-event magnitude.",
        ),
        ExtremeNightbladeAssassinationPassiveReviewEntry(
            "Pressure Points",
            False,
            IRRELEVANT,
            "Live-U50 Assassination passive review",
            "Adds Critical Chance rating per slotted Nightblade ability; it changes critical-event probability, not critical-heal magnitude.",
        ),
        ExtremeNightbladeAssassinationPassiveReviewEntry(
            "Hemorrhage",
            False,
            IRRELEVANT,
            "Live-U50 Assassination passive review",
            "Adds Critical Damage and grants Minor Savagery after a critical strike. Neither Critical Damage nor Weapon Critical rating increases Critical Healing magnitude.",
        ),
    )

    def items(self) -> tuple[ExtremeNightbladeAssassinationPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Assassination passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Assassination passive review contains duplicate passives")
        for row in rows:
            if row.objective_relevant or row.coverage_status != IRRELEVANT:
                raise ValueError(
                    f"Assassination healing review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status == IRRELEVANT for row in rows
        )
