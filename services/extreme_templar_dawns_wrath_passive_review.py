from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeTemplarDawnsWrathPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeTemplarDawnsWrathPassiveReview:
    """Exhaustive live-U50 Dawn's Wrath review for MOST Actual Heal.

    Illuminate is the one Dawn's Wrath passive that can change the numeric size
    of a healing event. A qualifying in-combat Dawn's Wrath cast grants Minor
    Sorcery, whose +10% Spell Damage is already owned by the canonical named-buff
    combat-state layer. Extreme therefore models only trigger/window legality and
    feeds the named buff into coefficient evaluation before the heal is scored.

    Enduring Rays changes selected Dawn's Wrath ability durations, Prism generates
    Ultimate, and Restoring Spirit reduces ability costs. Those mechanics affect
    damage cadence, Ultimate economy, or sustain rather than one maximum healing
    event and are objective-irrelevant here.
    """

    PASSIVE_NAMES = (
        "Enduring Rays",
        "Prism",
        "Illuminate",
        "Restoring Spirit",
    )

    _ENTRIES = (
        ExtremeTemplarDawnsWrathPassiveReviewEntry(
            "Enduring Rays",
            False,
            IRRELEVANT,
            "live-U50 Dawn's Wrath passive review",
            "Extends selected Dawn's Wrath ability durations and does not increase healing-event magnitude.",
        ),
        ExtremeTemplarDawnsWrathPassiveReviewEntry(
            "Prism",
            False,
            IRRELEVANT,
            "live-U50 Dawn's Wrath passive review",
            "Generates Ultimate after qualifying Dawn's Wrath casts; Ultimate economy does not enlarge one MOST Actual Heal event.",
        ),
        ExtremeTemplarDawnsWrathPassiveReviewEntry(
            "Illuminate",
            True,
            IMPLEMENTED,
            "ExtremeTemplarIlluminateCombatStateService + ExtremeTemplarConditionalActualHealService + canonical Minor Sorcery",
            "A caller-proven Illuminate window grants canonical Minor Sorcery before coefficient evaluation, increasing Spell Damage by 10% in live U50.",
        ),
        ExtremeTemplarDawnsWrathPassiveReviewEntry(
            "Restoring Spirit",
            False,
            IRRELEVANT,
            "live-U50 Dawn's Wrath passive review",
            "Reduces Health, Magicka, Stamina, and Ultimate costs; sustain and cost efficiency do not change the size of one healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeTemplarDawnsWrathPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Dawn's Wrath passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Dawn's Wrath passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Dawn's Wrath passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
