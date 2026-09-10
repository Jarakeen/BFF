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
    by MOST Actual Heal. Light Weaver's reviewed runtime utility is nevertheless
    modeled separately so broader Extreme-build consumers do not lose that class
    behavior merely because this particular objective ignores it.

    Update 51 is not live yet. This review intentionally remains bound to live
    Update 50 values until the application's game-version boundary advances.
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
            "Live U50 Mending is rank-aware: rank 1 increases healing done by up to 6% and rank 2 by up to 13%, in proportion to target missing Health.",
        ),
        ExtremeTemplarRestoringLightPassiveReviewEntry(
            "Sacred Ground",
            True,
            IMPLEMENTED,
            "ExtremeTemplarSacredGroundCombatStateService + canonical Minor Mending",
            "A caller-proven Sacred Ground window grants Minor Mending through CombatState at either passive rank; the post-area grace window is 2 seconds at rank 1 and 4 seconds at rank 2.",
        ),
        ExtremeTemplarRestoringLightPassiveReviewEntry(
            "Light Weaver",
            False,
            IRRELEVANT,
            "ExtremeTemplarLightWeaverService",
            "Reviewed runtime utility is modeled separately: qualifying Restoring Light ally healing below 50% Health grants 1/2 Ultimate by rank, and qualifying cast/channel activation in combat grants 2 seconds of automatic no-cost blocking on a 30s/15s cooldown. Neither changes MOST Actual Heal magnitude.",
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
