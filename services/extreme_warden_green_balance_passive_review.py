from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeWardenGreenBalancePassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeWardenGreenBalancePassiveReview:
    """Exhaustive Green Balance passive review for MOST Actual Heal.

    The family has four passives. Accelerated Growth and Emerald Moss can change
    the size of a reviewed healing event and are implemented by dedicated Extreme
    services. Nature's Gift is sustain-only, while Maturation grants Minor
    Toughness to the healed target; neither changes the numeric size of the
    healing event scored by the MOST Actual Heal objective.
    """

    PASSIVE_NAMES = (
        "Accelerated Growth",
        "Nature's Gift",
        "Emerald Moss",
        "Maturation",
    )

    _ENTRIES = (
        ExtremeWardenGreenBalancePassiveReviewEntry(
            "Accelerated Growth",
            True,
            IMPLEMENTED,
            "ExtremeWardenAcceleratedGrowthCombatStateService",
            "A caller-proven post-trigger window grants Major Mending through canonical CombatState. The triggering Green Balance heal is not assumed to benefit from the buff it creates.",
        ),
        ExtremeWardenGreenBalancePassiveReviewEntry(
            "Nature's Gift",
            False,
            IRRELEVANT,
            "Update 50 Green Balance Nature's Gift review",
            "Restores Magicka and Stamina after qualifying Green Balance overhealing. This is sustain behavior and does not change the numeric size of one MOST Actual Heal event.",
        ),
        ExtremeWardenGreenBalancePassiveReviewEntry(
            "Emerald Moss",
            True,
            IMPLEMENTED,
            "ExtremeWardenGreenBalanceHealingService",
            "Increases healing done by Green Balance abilities according to active-bar Green Balance slots and recorded passive rank.",
        ),
        ExtremeWardenGreenBalancePassiveReviewEntry(
            "Maturation",
            False,
            IRRELEVANT,
            "Green Balance Maturation review",
            "Grants Minor Toughness to the healed recipient. It changes recipient Max Health, not the calculated size of the healing event scored by MOST Actual Heal.",
        ),
    )

    def items(self) -> tuple[ExtremeWardenGreenBalancePassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Green Balance passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Green Balance passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Green Balance passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
