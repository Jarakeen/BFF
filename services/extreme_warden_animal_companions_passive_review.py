from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeWardenAnimalCompanionsPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeWardenAnimalCompanionsPassiveReview:
    """Exhaustive live-U50 Animal Companions review for MOST Actual Heal.

    Bond with Nature is a real caster self-heal and is modeled as its own
    triggered healing event. Savage Beast is Ultimate economy, Flourish is
    recovery, and Advanced Species is Critical Damage only; those three do not
    increase one healing event's magnitude.
    """

    PASSIVE_NAMES = (
        "Bond with Nature",
        "Savage Beast",
        "Flourish",
        "Advanced Species",
    )

    _ENTRIES = (
        ExtremeWardenAnimalCompanionsPassiveReviewEntry(
            "Bond with Nature",
            True,
            IMPLEMENTED,
            "ExtremeWardenBondWithNatureService + ExtremeWardenBondWithNatureHealingEventService",
            "Rank-aware 765/1530 base caster self-heal is triggered by a canonical Animal Companions effect-ended event and then scored with canonical healing modifiers.",
        ),
        ExtremeWardenAnimalCompanionsPassiveReviewEntry(
            "Savage Beast",
            False,
            IRRELEVANT,
            "Live-U50 Animal Companions passive review",
            "Generates Ultimate from Animal Companions casts in combat and does not change healing-event magnitude.",
        ),
        ExtremeWardenAnimalCompanionsPassiveReviewEntry(
            "Flourish",
            False,
            IRRELEVANT,
            "WardenPassiveInputResolver",
            "Increases Magicka and Stamina Recovery while an Animal Companions ability is slotted; modeled for sustain but not one-heal magnitude.",
        ),
        ExtremeWardenAnimalCompanionsPassiveReviewEntry(
            "Advanced Species",
            False,
            IRRELEVANT,
            "WardenPassiveInputResolver",
            "Increases Critical Damage per slotted Animal Companions ability, not Critical Healing.",
        ),
    )

    def items(self) -> tuple[ExtremeWardenAnimalCompanionsPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Animal Companions passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Animal Companions passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Animal Companions healing review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
