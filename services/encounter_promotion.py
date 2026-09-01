from __future__ import annotations

"""Review-only promotion policy for reconciled encounter facts.

This module does not write to the canonical encounter database. It classifies
reconciled facts into an explicit review queue so promotion remains deliberate.
"""

from dataclasses import dataclass
from typing import Iterable

from services.encounter_evidence import ReconciledEncounterFact


PROMOTION_ELIGIBLE = "eligible"
PROMOTION_REVIEW_REQUIRED = "review_required"
PROMOTION_BLOCKED = "blocked"
VALID_PROMOTION_STATUS = {
    PROMOTION_ELIGIBLE,
    PROMOTION_REVIEW_REQUIRED,
    PROMOTION_BLOCKED,
}


@dataclass(frozen=True)
class EncounterPromotionCandidate:
    fact: ReconciledEncounterFact
    promotion_status: str
    reason: str


def classify_encounter_fact_for_promotion(
    fact: ReconciledEncounterFact,
) -> EncounterPromotionCandidate:
    """Classify one reconciled fact without writing or choosing conflicting values."""

    if fact.status == "conflicting":
        return EncounterPromotionCandidate(
            fact=fact,
            promotion_status=PROMOTION_BLOCKED,
            reason="source values conflict; canonical promotion is blocked",
        )

    if fact.status == "corroborated":
        return EncounterPromotionCandidate(
            fact=fact,
            promotion_status=PROMOTION_ELIGIBLE,
            reason="two or more distinct sources agree on the same value",
        )

    return EncounterPromotionCandidate(
        fact=fact,
        promotion_status=PROMOTION_REVIEW_REQUIRED,
        reason="single-source evidence requires explicit human review",
    )


def build_encounter_promotion_preview(
    facts: Iterable[ReconciledEncounterFact],
) -> list[EncounterPromotionCandidate]:
    return [classify_encounter_fact_for_promotion(fact) for fact in facts]
