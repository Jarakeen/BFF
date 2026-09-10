from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeArcanistCurativeRuneformsPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeArcanistCurativeRuneformsPassiveReview:
    """Exhaustive Curative Runeforms passive review for MOST Actual Heal.

    Healing Tides can increase the numeric size of a healing event through
    generic Healing Done per active Crux and is already consumed by the
    conditional Actual Heal orchestration. Hideous Clarity and Erudition are
    sustain mechanics. Intricate Runeforms changes damage-shield cost/strength,
    not healing-event magnitude.

    Active abilities and morphs in Curative Runeforms are intentionally outside
    this four-passive denominator. Their healing mechanics remain covered by the
    wider Extreme healing-event/conditional services where applicable.
    """

    PASSIVE_NAMES = (
        "Healing Tides",
        "Hideous Clarity",
        "Erudition",
        "Intricate Runeforms",
    )

    _ENTRIES = (
        ExtremeArcanistCurativeRuneformsPassiveReviewEntry(
            "Healing Tides",
            True,
            IMPLEMENTED,
            "ExtremeArcanistCurativeRuneformsHealingService + ExtremeConditionalActualHealOptimizationService",
            "At reviewed max rank, generic Healing Done increases by 4% per active Crux; the conditional Actual Heal path requires explicit Crux state and preserves unresolved timing for Crux-consuming Remedy Cascade-family casts.",
        ),
        ExtremeArcanistCurativeRuneformsPassiveReviewEntry(
            "Hideous Clarity",
            False,
            IRRELEVANT,
            "Curative Runeforms Hideous Clarity review",
            "Restores Magicka and Stamina when Crux is generated; this is sustain rather than healing-event magnitude.",
        ),
        ExtremeArcanistCurativeRuneformsPassiveReviewEntry(
            "Erudition",
            False,
            IRRELEVANT,
            "Curative Runeforms Erudition review",
            "Increases Magicka and Stamina Recovery; this affects sustain rather than the size of MOST Actual Heal.",
        ),
        ExtremeArcanistCurativeRuneformsPassiveReviewEntry(
            "Intricate Runeforms",
            False,
            IRRELEVANT,
            "Curative Runeforms Intricate Runeforms review",
            "With a Curative Runeforms ability slotted, reduces damage-shield cost and increases damage-shield strength; it does not increase a healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeArcanistCurativeRuneformsPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Curative Runeforms passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Curative Runeforms passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Curative Runeforms passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
