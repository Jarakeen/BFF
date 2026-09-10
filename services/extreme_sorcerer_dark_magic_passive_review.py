from __future__ import annotations

from dataclasses import dataclass


IMPLEMENTED = "implemented"
IRRELEVANT = "irrelevant"
EXPLICITLY_UNSUPPORTED = "explicitly_unsupported"


@dataclass(frozen=True)
class ExtremeSorcererDarkMagicPassiveReviewEntry:
    passive_name: str
    objective_relevant: bool
    coverage_status: str
    evidence: str
    detail: str


class ExtremeSorcererDarkMagicPassiveReview:
    """Exhaustive live-U50 Dark Magic passive review for MOST Actual Heal.

    Blood Magic is objective-relevant and its two live-U50 branches are now
    resolved explicitly by ``ExtremeSorcererBloodMagicService``. Below full
    Health, casting a costed Dark Magic ability produces a separate Max-Health-
    scaled self-heal event. At full Health, the higher of Max Magicka or Stamina
    receives a 10% increase for 10 seconds. The family remains explicitly
    unsupported until the conditional Actual Heal optimizer consumes that
    resource-window result and exposes the separate self-heal event without
    combining recipient-distinct healing.

    Unholy Knowledge and Persistence only reduce ability costs. Exploitation
    grants Minor Prophecy, which changes Spell Critical chance but not the size
    of the critical event scored by MOST Actual Heal.
    """

    PASSIVE_NAMES = (
        "Unholy Knowledge",
        "Blood Magic",
        "Persistence",
        "Exploitation",
    )

    _ENTRIES = (
        ExtremeSorcererDarkMagicPassiveReviewEntry(
            "Unholy Knowledge",
            False,
            IRRELEVANT,
            "Dark Magic Unholy Knowledge review",
            "Reduces non-Core ability Health, Magicka, and Stamina costs; this is sustain/executability rather than one-event heal magnitude.",
        ),
        ExtremeSorcererDarkMagicPassiveReviewEntry(
            "Blood Magic",
            True,
            EXPLICITLY_UNSUPPORTED,
            "ExtremeSorcererBloodMagicService",
            "Both live-U50 branches are now resolved with explicit trigger, passive, subclass, and caster-Health proof: below full Health, Blood Magic creates a separate Max-Health-scaled self-heal; at full Health, it creates the 10-second higher-resource window. Conditional Actual Heal orchestration must still consume that resource window and expose the self-heal event without adding it to unrelated target healing.",
        ),
        ExtremeSorcererDarkMagicPassiveReviewEntry(
            "Persistence",
            False,
            IRRELEVANT,
            "Dark Magic Persistence review",
            "Reduces the cost of the next Health, Magicka, or Stamina ability after blocking; it does not change one healing event's numeric size.",
        ),
        ExtremeSorcererDarkMagicPassiveReviewEntry(
            "Exploitation",
            False,
            IRRELEVANT,
            "Dark Magic Exploitation review",
            "Grants Minor Prophecy after casting Dark Magic, increasing Spell Critical chance. MOST Actual Heal conditions on the event critting and does not multiply by critical probability.",
        ),
    )

    def items(self) -> tuple[ExtremeSorcererDarkMagicPassiveReviewEntry, ...]:
        rows = self._ENTRIES
        names = tuple(row.passive_name for row in rows)
        if names != self.PASSIVE_NAMES:
            raise ValueError(
                "Dark Magic passive review must exactly match the canonical reviewed passive roster"
            )
        if len(names) != len(set(names)):
            raise ValueError("Dark Magic passive review contains duplicate passives")
        for row in rows:
            valid = (
                {IRRELEVANT}
                if not row.objective_relevant
                else {IMPLEMENTED, EXPLICITLY_UNSUPPORTED}
            )
            if row.coverage_status not in valid:
                raise ValueError(
                    f"Dark Magic passive review has inconsistent coverage for {row.passive_name}"
                )
        return rows

    @property
    def complete(self) -> bool:
        rows = self.items()
        return len(rows) == len(self.PASSIVE_NAMES) and all(
            row.coverage_status in {IMPLEMENTED, IRRELEVANT, EXPLICITLY_UNSUPPORTED}
            for row in rows
        )

    @property
    def implemented(self) -> bool:
        return all(
            row.coverage_status != EXPLICITLY_UNSUPPORTED
            for row in self.items()
            if row.objective_relevant
        )
