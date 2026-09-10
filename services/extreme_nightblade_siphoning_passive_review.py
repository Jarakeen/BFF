from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeNightbladeSiphoningPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeNightbladeSiphoningPassiveReview:
    """Exhaustive Siphoning passive review for MOST Actual Heal.

    The family has four passives. Magicka Flood can change heal coefficients by
    increasing Max Magicka and Max Stamina while a Siphoning ability is slotted,
    and Soul Siphoner directly increases Healing Done for each slotted Siphoning
    ability. Catalyst and Transfer generate Ultimate and therefore do not change
    the numeric size of one healing event scored by MOST Actual Heal.
    """

    PASSIVE_NAMES = (
        "Catalyst",
        "Magicka Flood",
        "Soul Siphoner",
        "Transfer",
    )

    _ENTRIES = (
        ExtremeNightbladeSiphoningPassiveReviewEntry(
            "Catalyst",
            False,
            IRRELEVANT,
            "Siphoning Catalyst review",
            "Generates Ultimate after drinking a potion. Ultimate economy does not change the numeric size of one MOST Actual Heal event.",
        ),
        ExtremeNightbladeSiphoningPassiveReviewEntry(
            "Magicka Flood",
            True,
            IMPLEMENTED,
            "NightbladePassiveInputResolver + BuildCalculationContextFactory",
            "At reviewed Update 46+ max rank, a Siphoning ability slotted on the active bar adds 6% Max Magicka and Max Stamina through canonical additive primary-resource percentage inputs before ESO rounding.",
        ),
        ExtremeNightbladeSiphoningPassiveReviewEntry(
            "Soul Siphoner",
            True,
            IMPLEMENTED,
            "ExtremeNightbladeSiphoningHealingService",
            "At reviewed max rank, each Siphoning ability slotted on the active bar increases generic Healing Done by 3% through the Extreme healing-event path.",
        ),
        ExtremeNightbladeSiphoningPassiveReviewEntry(
            "Transfer",
            False,
            IRRELEVANT,
            "Siphoning Transfer review",
            "Generates Ultimate after casting a Siphoning ability in combat. Ultimate generation affects cadence/resource economy, not the numeric size of one MOST Actual Heal event.",
        ),
    )

    def items(self) -> tuple[ExtremeNightbladeSiphoningPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Siphoning passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Siphoning passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Siphoning passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
