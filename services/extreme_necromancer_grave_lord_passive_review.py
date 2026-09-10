from __future__ import annotations

from dataclasses import dataclass


IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeNecromancerGraveLordPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeNecromancerGraveLordPassiveReview:
    """Live-U50 Grave Lord passive review for MOST Actual Heal.

    None of the four Grave Lord passives enlarges the numeric magnitude of one
    healing event. Reusable Parts is cost economy; Death Knell changes offensive
    Critical Strike Chance against low-Health enemies; Dismember adds offensive
    penetration; Rapid Rot increases damage-over-time damage.

    Grave Lord active skills can still contain healing-adjacent behavior (for
    example the Boneyard synergy), but that is active-skill behavior rather than
    a reason to treat an unrelated class passive as healing magnitude.
    """

    PASSIVE_NAMES = (
        "Reusable Parts",
        "Death Knell",
        "Dismember",
        "Rapid Rot",
    )

    _ENTRIES = (
        ExtremeNecromancerGraveLordPassiveReviewEntry(
            "Reusable Parts",
            False,
            IRRELEVANT,
            "Live-U50 Grave Lord passive review",
            "Reduces the cost of the next qualifying Sacrificial Bones, Skeletal Mage, or Spirit Mender after one dies. Cost economy does not enlarge one healing event.",
        ),
        ExtremeNecromancerGraveLordPassiveReviewEntry(
            "Death Knell",
            False,
            IRRELEVANT,
            "Live-U50 Grave Lord passive review",
            "With a Grave Lord ability slotted, increases offensive Critical Strike Chance against enemies under 33% Health. This changes the chance to critically strike an enemy, not Critical Healing magnitude for a proven critical heal.",
        ),
        ExtremeNecromancerGraveLordPassiveReviewEntry(
            "Dismember",
            False,
            IRRELEVANT,
            "Live-U50 Grave Lord passive review",
            "While a Grave Lord ability is active, increases Spell and Physical Penetration. Penetration affects damage against enemy resistance and does not enlarge one healing event.",
        ),
        ExtremeNecromancerGraveLordPassiveReviewEntry(
            "Rapid Rot",
            False,
            IRRELEVANT,
            "Live-U50 Grave Lord passive review",
            "Increases damage done with damage-over-time effects. Damage-done modifiers do not enlarge healing-event magnitude.",
        ),
    )

    def items(self) -> tuple[ExtremeNecromancerGraveLordPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Grave Lord passive review must exactly match the live-U50 reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Grave Lord passive review contains duplicate passives")
        if any(row.objective_relevant for row in rows):
            raise ValueError(
                "Grave Lord passives must remain objective-irrelevant for MOST Actual Heal"
            )
        if any(row.coverage_status != IRRELEVANT for row in rows):
            raise ValueError("Objective-irrelevant Grave Lord passives must remain irrelevant")
        return rows

    @property
    def complete(self) -> bool:
        self.items()
        return True
