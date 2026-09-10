from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeNecromancerLivingDeathPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeNecromancerLivingDeathPassiveReview:
    """Exhaustive Living Death passive review for MOST Actual Heal.

    The family has four passives. Curative Curse can change the size of a
    reviewed healing event and is implemented by the dedicated Extreme service.
    Near-Death Experience changes healing Critical Strike Chance, which affects
    the probability of a critical heal rather than the size of the maximum event
    when that event crits. Corpse Consumption generates Ultimate and Undead
    Confederate grants recovery, so both are outside this objective's heal-size
    math.
    """

    PASSIVE_NAMES = (
        "Curative Curse",
        "Near-Death Experience",
        "Corpse Consumption",
        "Undead Confederate",
    )

    _ENTRIES = (
        ExtremeNecromancerLivingDeathPassiveReviewEntry(
            "Curative Curse",
            True,
            IMPLEMENTED,
            "ExtremeNecromancerLivingDeathHealingService",
            "While an explicit healer negative-effect state is active, the reviewed passive contributes generic Healing Done through the conditional Extreme healing path.",
        ),
        ExtremeNecromancerLivingDeathPassiveReviewEntry(
            "Near-Death Experience",
            False,
            IRRELEVANT,
            "Update 46 Living Death review + MOST Actual Heal objective contract",
            "Increases healing Critical Strike Chance in proportion to target missing Health while a Living Death ability is slotted. Critical chance changes whether a heal crits, not the numeric size of the maximum critical healing event scored by MOST Actual Heal.",
        ),
        ExtremeNecromancerLivingDeathPassiveReviewEntry(
            "Corpse Consumption",
            False,
            IRRELEVANT,
            "Living Death Corpse Consumption review",
            "Generates Ultimate after consuming a corpse. Ultimate economy can affect rotation or ability availability, but it does not directly change the numeric size of one healing event scored by MOST Actual Heal.",
        ),
        ExtremeNecromancerLivingDeathPassiveReviewEntry(
            "Undead Confederate",
            False,
            IRRELEVANT,
            "Update 46 Living Death review",
            "Increases Health, Magicka, and Stamina Recovery while a Necromantic pet is active. This is sustain behavior and does not directly change the numeric size of one MOST Actual Heal event.",
        ),
    )

    def items(self) -> tuple[ExtremeNecromancerLivingDeathPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Living Death passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Living Death passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Living Death passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
