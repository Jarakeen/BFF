from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.rotation_dd_periodic_review_status_service import (
    RotationDDPeriodicReviewStatus,
    RotationDDPeriodicReviewStatusService,
)
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDDamageCoverageBlocker,
    RotationDDWholePlanDamageCoverageAudit,
)


class RotationDDDamageBlockerDisposition(str, Enum):
    ACTIONABLE = "actionable"
    PARKED_EVIDENCE = "parked_evidence"


@dataclass(frozen=True)
class RotationDDDamageBlockerTriage:
    blocker: RotationDDDamageCoverageBlocker
    disposition: RotationDDDamageBlockerDisposition
    disposition_reason: str | None = None


@dataclass(frozen=True)
class RotationDDWholePlanDamageBlockerTriageReport:
    candidate_id: str
    blockers: tuple[RotationDDDamageBlockerTriage, ...]

    @property
    def actionable(self) -> tuple[RotationDDDamageBlockerTriage, ...]:
        return tuple(
            item
            for item in self.blockers
            if item.disposition is RotationDDDamageBlockerDisposition.ACTIONABLE
        )

    @property
    def parked(self) -> tuple[RotationDDDamageBlockerTriage, ...]:
        return tuple(
            item
            for item in self.blockers
            if item.disposition is RotationDDDamageBlockerDisposition.PARKED_EVIDENCE
        )


class RotationDDWholePlanDamageBlockerTriageService:
    """Prioritize whole-plan DD blockers without weakening fail-closed evidence.

    Coverage blockers remain authoritative. This service only distinguishes unresolved
    consequences tied to intentionally parked periodic reviews from blockers whose
    evidence work is still actionable. It never converts parked damage to zero or marks
    the underlying coverage audit complete.
    """

    _PERIODIC_REASON_MARKERS = (
        "reviewed periodic runtime semantics are unavailable",
        "periodic magnitude timing policy is unavailable",
        "periodic runtime",
    )

    def __init__(
        self,
        periodic_status_service: RotationDDPeriodicReviewStatusService | None = None,
    ) -> None:
        self.periodic_status_service = (
            periodic_status_service or RotationDDPeriodicReviewStatusService()
        )

    def classify(
        self,
        audit: RotationDDWholePlanDamageCoverageAudit,
    ) -> RotationDDWholePlanDamageBlockerTriageReport:
        dispositions = self.periodic_status_service.dispositions()
        parked_by_skill = {
            item.entry.skill_entity_id.casefold(): item
            for item in dispositions
            if item.status is RotationDDPeriodicReviewStatus.PARKED
        }

        result: list[RotationDDDamageBlockerTriage] = []
        for blocker in audit.blockers:
            action_name = str(blocker.action_name or "").strip().casefold()
            reason = str(blocker.reason or "").strip()
            parked_review = parked_by_skill.get(action_name)
            periodic_reason = any(
                marker in reason.casefold() for marker in self._PERIODIC_REASON_MARKERS
            )
            if parked_review is not None and periodic_reason:
                result.append(
                    RotationDDDamageBlockerTriage(
                        blocker=blocker,
                        disposition=RotationDDDamageBlockerDisposition.PARKED_EVIDENCE,
                        disposition_reason=parked_review.reason,
                    )
                )
                continue
            result.append(
                RotationDDDamageBlockerTriage(
                    blocker=blocker,
                    disposition=RotationDDDamageBlockerDisposition.ACTIONABLE,
                )
            )

        return RotationDDWholePlanDamageBlockerTriageReport(
            candidate_id=audit.candidate_id,
            blockers=tuple(result),
        )


__all__ = [
    "RotationDDDamageBlockerDisposition",
    "RotationDDDamageBlockerTriage",
    "RotationDDWholePlanDamageBlockerTriageReport",
    "RotationDDWholePlanDamageBlockerTriageService",
]
