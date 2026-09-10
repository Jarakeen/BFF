from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeDragonknightDraconicPowerPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeDragonknightDraconicPowerPassiveReview:
    """Live-U50 Draconic Power review for MOST Actual Heal.

    Elder Dragon is the only passive in this family that can enlarge a heal
    coefficient. Activating a Draconic Power ability grants Minor Brutality for
    20 seconds, and the canonical named-buff layer applies its 10% Weapon Damage
    increase before coefficient evaluation. The passive's separate Health
    Recovery branch is not part of one healing-event magnitude.
    """

    PASSIVE_NAMES = (
        "Burnished Scales",
        "World in Ruin",
        "Elder Dragon",
        "The Storm Voice",
    )

    _ENTRIES = (
        ExtremeDragonknightDraconicPowerPassiveReviewEntry(
            "Burnished Scales",
            False,
            IRRELEVANT,
            "Live-U50 Draconic Power passive review",
            "Increases the amount of damage blocked; it does not enlarge one healing event.",
        ),
        ExtremeDragonknightDraconicPowerPassiveReviewEntry(
            "World in Ruin",
            False,
            IRRELEVANT,
            "Live-U50 Draconic Power passive review",
            "Increases area and damage-over-time damage rather than healing-event magnitude.",
        ),
        ExtremeDragonknightDraconicPowerPassiveReviewEntry(
            "Elder Dragon",
            True,
            IMPLEMENTED,
            "ExtremeDragonknightElderDragonCombatStateService + ExtremeDragonknightConditionalActualHealService + canonical Minor Brutality",
            "An explicit active post-Draconic-Power window grants canonical Minor Brutality before heal coefficient evaluation. Passive rank and class-line legality are proven; no uptime is invented.",
        ),
        ExtremeDragonknightDraconicPowerPassiveReviewEntry(
            "The Storm Voice",
            False,
            IRRELEVANT,
            "Live-U50 Draconic Power passive review",
            "Restores resources after casting an Ultimate; resource sustain does not enlarge the numeric magnitude of one healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeDragonknightDraconicPowerPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Draconic Power passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Draconic Power passive review contains duplicate passives")
        relevant = tuple(row for row in rows if row.objective_relevant)
        if len(relevant) != 1 or relevant[0].passive_name != "Elder Dragon":
            raise ValueError(
                "Draconic Power healing review must identify only Elder Dragon as objective-relevant"
            )
        if relevant[0].coverage_status != IMPLEMENTED:
            raise ValueError("Elder Dragon must remain implemented for MOST Actual Heal")
        if any(
            row.coverage_status != IRRELEVANT
            for row in rows
            if not row.objective_relevant
        ):
            raise ValueError("Objective-irrelevant Draconic Power passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return True
