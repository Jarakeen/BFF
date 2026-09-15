from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.skill_coefficient_repository import ability_entity_id
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
    RUNTIME_INPUT_REQUIRED = "runtime_input_required"


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

    @property
    def runtime_input_required(self) -> tuple[RotationDDDamageBlockerTriage, ...]:
        return tuple(
            item
            for item in self.blockers
            if item.disposition is RotationDDDamageBlockerDisposition.RUNTIME_INPUT_REQUIRED
        )


class RotationDDWholePlanDamageBlockerTriageService:
    """Prioritize whole-plan DD blockers without weakening fail-closed evidence.

    Coverage blockers remain authoritative. This service distinguishes intentionally
    parked source-review gaps, caller/runtime-owned exact evidence gaps, and
    engineering work that is still actionable. No disposition converts unresolved
    damage to zero or marks the underlying coverage audit complete.
    """

    _PERIODIC_REASON_MARKERS = (
        "reviewed periodic runtime semantics are unavailable",
        "periodic magnitude timing policy is unavailable",
        "periodic runtime",
        "periodic target-health timing is not source-reviewed",
        "periodic target-health conditional timing is unresolved",
    )
    _PARKED_SOURCE_REVIEW_REASON_MARKERS = (
        "lightning staff light-attack combat semantics remain unresolved",
    )
    _RUNTIME_INPUT_REASON_MARKERS = (
        "requires exact runtime anchor evidence",
        "requires authoritative target combatstate",
        "requires exact-time runtime",
        "target-health conditional damage requires an exact runtime snapshot",
        "target-health conditional damage requires a target identity",
        "is absent from snapshot",
        "health is unknown",
        "threshold state is unknown",
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
            item.entry.skill_entity_id: item
            for item in dispositions
            if item.status is RotationDDPeriodicReviewStatus.PARKED
        }

        result: list[RotationDDDamageBlockerTriage] = []
        for blocker in audit.blockers:
            action_name = ability_entity_id(blocker.action_name or "")
            reason = str(blocker.reason or "").strip()
            reason_folded = reason.casefold()
            parked_review = parked_by_skill.get(action_name)
            periodic_reason = any(
                marker in reason_folded for marker in self._PERIODIC_REASON_MARKERS
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
            if any(
                marker in reason_folded
                for marker in self._PARKED_SOURCE_REVIEW_REASON_MARKERS
            ):
                result.append(
                    RotationDDDamageBlockerTriage(
                        blocker=blocker,
                        disposition=RotationDDDamageBlockerDisposition.PARKED_EVIDENCE,
                        disposition_reason=(
                            "Lightning Staff light-attack modifier semantics require source review; "
                            "the preserved formula contract still carries Heavy-Attack/Empower/DoT-shaped buckets"
                        ),
                    )
                )
                continue
            if any(marker in reason_folded for marker in self._RUNTIME_INPUT_REASON_MARKERS):
                result.append(
                    RotationDDDamageBlockerTriage(
                        blocker=blocker,
                        disposition=RotationDDDamageBlockerDisposition.RUNTIME_INPUT_REQUIRED,
                        disposition_reason=(
                            "reviewed semantics exist, but this run lacks exact caller/runtime evidence"
                        ),
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
