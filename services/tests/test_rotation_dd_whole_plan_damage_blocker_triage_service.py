from types import SimpleNamespace

from minmax.rotation_plan import RotationActionKind
from services.rotation_dd_periodic_review_status_service import (
    RotationDDPeriodicReviewStatusService,
)
from services.rotation_dd_whole_plan_damage_blocker_triage_service import (
    RotationDDDamageBlockerDisposition,
    RotationDDWholePlanDamageBlockerTriageService,
)
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDDamageCoverageBlocker,
    RotationDDWholePlanDamageCoverageAudit,
)


class _ReviewService:
    def load(self):
        return (
            SimpleNamespace(
                skill_entity_id="unnerving_boneyard",
                coefficient_number=1,
                executable_complete=False,
            ),
            SimpleNamespace(
                skill_entity_id="stampede",
                coefficient_number=2,
                executable_complete=True,
            ),
        )


def _blocker(name: str, reason: str) -> RotationDDDamageCoverageBlocker:
    return RotationDDDamageCoverageBlocker(
        action_kind=RotationActionKind.SKILL,
        action_name=name,
        reason=reason,
        occurrences=((1.0, 1),),
    )


def test_triage_marks_known_parked_periodic_gap_from_display_name_without_resolving_it() -> None:
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="candidate",
        total_damage_actions=2,
        resolved_damage_actions=0,
        unresolved_damage_actions=2,
        blockers=(
            _blocker(
                "Unnerving Boneyard",
                "Unnerving Boneyard: coefficient 1 reviewed periodic runtime semantics are unavailable",
            ),
            _blocker("Other Skill", "direct damage coefficient unavailable"),
        ),
    )
    service = RotationDDWholePlanDamageBlockerTriageService(
        periodic_status_service=RotationDDPeriodicReviewStatusService(_ReviewService())
    )

    result = service.classify(audit)

    assert audit.complete is False
    assert len(result.parked) == 1
    assert len(result.actionable) == 1
    assert result.parked[0].blocker.action_name == "Unnerving Boneyard"
    assert result.parked[0].disposition is RotationDDDamageBlockerDisposition.PARKED_EVIDENCE
    assert "first-tick offset" in (result.parked[0].disposition_reason or "")
    assert result.actionable[0].blocker.action_name == "Other Skill"


def test_same_skill_nonperiodic_blocker_remains_actionable() -> None:
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="candidate",
        total_damage_actions=1,
        resolved_damage_actions=0,
        unresolved_damage_actions=1,
        blockers=(
            _blocker("Unnerving Boneyard", "target resistance unavailable"),
        ),
    )
    service = RotationDDWholePlanDamageBlockerTriageService(
        periodic_status_service=RotationDDPeriodicReviewStatusService(_ReviewService())
    )

    result = service.classify(audit)

    assert result.parked == ()
    assert len(result.actionable) == 1
