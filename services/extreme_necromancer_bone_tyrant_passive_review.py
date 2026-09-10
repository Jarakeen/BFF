from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeNecromancerBoneTyrantPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeNecromancerBoneTyrantPassiveReview:
    """Live-U50 Bone Tyrant review for MOST Actual Heal.

    ``Health Avarice`` increases Healing Received for each Bone Tyrant ability
    slotted on the active bar. ``Last Gasp`` adds flat Max Health. Both can
    enlarge a legal healing event and therefore belong in the shared canonical
    character snapshot rather than in an Extreme-only multiplier.
    """

    PASSIVE_NAMES = (
        "Death Gleaning",
        "Disdain Harm",
        "Health Avarice",
        "Last Gasp",
    )

    _ENTRIES = (
        ExtremeNecromancerBoneTyrantPassiveReviewEntry(
            "Death Gleaning",
            False,
            IRRELEVANT,
            "Live-U50 Bone Tyrant passive review",
            "Restores Magicka and Stamina when a nearby combat enemy dies while a Bone Tyrant ability is slotted; sustain does not enlarge one healing event.",
        ),
        ExtremeNecromancerBoneTyrantPassiveReviewEntry(
            "Disdain Harm",
            False,
            IRRELEVANT,
            "Live-U50 Bone Tyrant passive review",
            "Reduces damage taken from damage-over-time abilities while a Bone Tyrant ability is active; mitigation does not enlarge one healing event.",
        ),
        ExtremeNecromancerBoneTyrantPassiveReviewEntry(
            "Health Avarice",
            True,
            IMPLEMENTED,
            "NecromancerPassiveInputResolver + BuildCalculationContextFactory",
            "Rank-aware Healing Received is added to canonical received-side healing math per Bone Tyrant ability slotted on the active bar. Slot count and class-line legality must be explicitly proven.",
        ),
        ExtremeNecromancerBoneTyrantPassiveReviewEntry(
            "Last Gasp",
            True,
            IMPLEMENTED,
            "NecromancerPassiveInputResolver + BuildCalculationContextFactory",
            "Rank-aware flat Max Health is inserted into canonical primary-resource inputs before ESO rounding and before any Max-Health-scaled healing coefficient is evaluated.",
        ),
    )

    def items(self) -> tuple[ExtremeNecromancerBoneTyrantPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Bone Tyrant passive review must exactly match the reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Bone Tyrant passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if tuple(row.passive_name for row in relevant) != (
            "Health Avarice",
            "Last Gasp",
        ):
            raise ValueError(
                "Bone Tyrant healing review must identify Health Avarice and Last Gasp as objective-relevant"
            )
        if any(row.coverage_status != IMPLEMENTED for row in relevant):
            raise ValueError("Relevant Bone Tyrant passives must remain implemented")
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Bone Tyrant passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return True
