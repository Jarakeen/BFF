from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"


@dataclass(frozen=True)
class ExtremeTemplarRestoringLightPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeTemplarRestoringLightPassiveReview:
    """Exhaustive live-U50 Restoring Light passive review for MOST Actual Heal.

    Mending and Sacred Ground can change the numeric size of a healing event and
    are modeled by dedicated Extreme services. Light Weaver and Master Ritualist
    are utility/resurrection mechanics and do not change the heal magnitude scored
    by MOST Actual Heal.

    Update 51 is not live yet. Its announced Mending change is deliberately not
    applied to this live-U50 review; the version boundary must be updated when U51
    becomes the active game update.
    """

    PASSIVE_NAMES = (
        "Mending",
        "Sacred Ground",
        "Light Weaver",
        "Master Ritualist",
    )

    _ENTRIES = (
        ExtremeTemplarRestoringLightPassiveReviewEntry(
            "Mending",
            True,
            IMPLEMENTED,
            "ExtremeTemplarRestoringLightHealingService",
            "Live U50 max rank increases Restoring Light healing by up to 12% in proportion to target missing Health.",
        ),
        ExtremeTemplarRestoringLightPassiveReviewEntry(
            "Sacred Ground",
            True,
            IMPLEMENTED,
            "ExtremeTemplarSacredGroundCombatStateService + canonical Minor Mending",
            "A caller-proven Sacred Ground window grants Minor Mending through CombatState; canonical named-buff math owns the 8% Healing Done value.",
        ),
        ExtremeTemplarRestoringLightPassiveReviewEntry(
            "Light Weaver",
            False,
            IRRELEVANT,
            "Restoring Light Light Weaver review",
            "Grants ally Ultimate after qualifying healing and provides automatic blocking during cast/channel use; it does not increase the numeric size of MOST Actual Heal.",
        ),
        ExtremeTemplarRestoringLightPassiveReviewEntry(
            "Master Ritualist",
            False,
            IRRELEVANT,
            "Restoring Light Master Ritualist review",
            "Changes resurrection speed, resurrected ally Health, and Soul Gem behavior rather than the size of a healing event.",
        ),
    )

    def items(self) -> tuple[ExtremeTemplarRestoringLightPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Restoring Light passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Restoring Light passive review contains duplicate passives")
        for row in rows:
            expected = IMPLEMENTED if row.objective_relevant else IRRELEVANT
            if row.coverage_status != expected:
                raise ValueError(
                    f"Restoring Light passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT} for row in rows
        )
