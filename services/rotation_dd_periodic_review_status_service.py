from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewEntry,
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


class RotationDDPeriodicReviewStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    PARKED = "parked"


_PARKED_REASONS: dict[tuple[str, int], str] = {
    ("unnerving_boneyard", 1): (
        "current corpus cannot resolve exact first-tick offset or magnitude policy"
    ),
    ("detonating_siphon", 1): (
        "production geometry/timing remains fail-closed pending controlled spatial evidence"
    ),
    ("flawless_dawnbreaker", 2): (
        "current corpus has only two casts and no cast-track-linked periodic candidate"
    ),
    ("skeletal_archer", 1): (
        "current corpus exposes no explicit pet-to-owner linkage for candidate 122774"
    ),
    ("scalding_rune", 2): (
        "current corpus has no stable-state magnitude controls"
    ),
    ("meteor", 2): (
        "current corpus has no identifiable Meteor-family cast/damage evidence"
    ),
}


@dataclass(frozen=True)
class RotationDDPeriodicReviewDisposition:
    entry: RotationDDPeriodicRuntimeSemanticsReviewEntry
    status: RotationDDPeriodicReviewStatus
    reason: str | None = None


class RotationDDPeriodicReviewStatusService:
    """Classify reviewed DD periodic components without changing runtime semantics.

    COMPLETE means every executable field is reviewed. PARKED means the current evidence
    source is known to be exhausted or non-discriminating. PARTIAL means evidence work
    remains active. None of these labels weakens fail-closed runtime behavior.
    """

    def __init__(
        self,
        review_service: RotationDDPeriodicRuntimeSemanticsReviewService | None = None,
    ) -> None:
        self.review_service = review_service or RotationDDPeriodicRuntimeSemanticsReviewService()

    def dispositions(self) -> tuple[RotationDDPeriodicReviewDisposition, ...]:
        result: list[RotationDDPeriodicReviewDisposition] = []
        for entry in self.review_service.load():
            key = (entry.skill_entity_id, entry.coefficient_number)
            if entry.executable_complete:
                status = RotationDDPeriodicReviewStatus.COMPLETE
                reason = None
            elif key in _PARKED_REASONS:
                status = RotationDDPeriodicReviewStatus.PARKED
                reason = _PARKED_REASONS[key]
            else:
                status = RotationDDPeriodicReviewStatus.PARTIAL
                reason = None
            result.append(
                RotationDDPeriodicReviewDisposition(
                    entry=entry,
                    status=status,
                    reason=reason,
                )
            )
        return tuple(result)

    def by_component(self) -> dict[tuple[str, int], RotationDDPeriodicReviewDisposition]:
        return {
            (item.entry.skill_entity_id, item.entry.coefficient_number): item
            for item in self.dispositions()
        }

    def parked_for_skill(self, skill_entity_id: str) -> tuple[RotationDDPeriodicReviewDisposition, ...]:
        identity = str(skill_entity_id or "").strip().casefold()
        return tuple(
            item
            for item in self.dispositions()
            if item.status is RotationDDPeriodicReviewStatus.PARKED
            and item.entry.skill_entity_id.casefold() == identity
        )


__all__ = [
    "RotationDDPeriodicReviewDisposition",
    "RotationDDPeriodicReviewStatus",
    "RotationDDPeriodicReviewStatusService",
]
