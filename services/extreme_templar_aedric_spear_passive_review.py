from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeTemplarAedricSpearPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeTemplarAedricSpearPassiveReview:
    """Exhaustive live-U50 Aedric Spear review for MOST Actual Heal.

    Balanced Warrior changes Weapon and Spell Damage and therefore changes heal
    coefficients that scale from offensive power. It is routed through the
    canonical ``BuildCalculationContextFactory`` via ``TemplarPassiveInputResolver``.

    Piercing Spear increases Critical Damage rather than Critical Healing. Spear
    Wall grants Minor Berserk/Minor Protection after activating an Aedric Spear
    ability, affecting damage done and damage taken rather than healing-event
    magnitude. Burning Light is a damage proc. Those mechanics remain visible in
    this review but are outside the MOST Actual Heal objective denominator.
    """

    PASSIVE_NAMES = (
        "Piercing Spear",
        "Spear Wall",
        "Burning Light",
        "Balanced Warrior",
    )

    _ENTRIES = (
        ExtremeTemplarAedricSpearPassiveReviewEntry(
            "Piercing Spear",
            False,
            IRRELEVANT,
            "live-U50 Aedric Spear passive review",
            "With an Aedric Spear ability slotted, Piercing Spear increases Critical Damage, not Critical Healing, so it cannot enlarge MOST Actual Heal.",
        ),
        ExtremeTemplarAedricSpearPassiveReviewEntry(
            "Spear Wall",
            False,
            IRRELEVANT,
            "live-U50 Aedric Spear passive review",
            "Activating an Aedric Spear ability grants Minor Berserk and Minor Protection; those modify damage done/taken rather than healing-event magnitude.",
        ),
        ExtremeTemplarAedricSpearPassiveReviewEntry(
            "Burning Light",
            False,
            IRRELEVANT,
            "live-U50 Aedric Spear passive review",
            "Burning Light is a damage proc and does not modify a healing event.",
        ),
        ExtremeTemplarAedricSpearPassiveReviewEntry(
            "Balanced Warrior",
            True,
            IMPLEMENTED,
            "TemplarPassiveInputResolver + BuildCalculationContextFactory",
            "At reviewed max rank Balanced Warrior adds 6% Weapon Damage and 6% Spell Damage to the canonical percent buckets; offensive-power-scaled heals therefore inherit the increase through normal coefficient math.",
        ),
    )

    def items(self) -> tuple[ExtremeTemplarAedricSpearPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Aedric Spear passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Aedric Spear passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Aedric Spear passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
