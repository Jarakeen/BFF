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


def _service() -> RotationDDWholePlanDamageBlockerTriageService:
    return RotationDDWholePlanDamageBlockerTriageService(
        periodic_status_service=RotationDDPeriodicReviewStatusService(_ReviewService())
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

    result = _service().classify(audit)

    assert audit.complete is False
    assert len(result.parked) == 1
    assert len(result.actionable) == 1
    assert result.runtime_input_required == ()
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

    result = _service().classify(audit)

    assert result.parked == ()
    assert result.runtime_input_required == ()
    assert len(result.actionable) == 1


def test_exact_impact_anchor_gap_is_runtime_input_not_engineering_work() -> None:
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="candidate",
        total_damage_actions=1,
        resolved_damage_actions=0,
        unresolved_damage_actions=1,
        blockers=(
            _blocker(
                "Stampede",
                "Stampede coefficient 2: reviewed activation anchor impact requires exact runtime anchor evidence",
            ),
        ),
    )

    result = _service().classify(audit)

    assert result.actionable == ()
    assert result.parked == ()
    assert len(result.runtime_input_required) == 1
    item = result.runtime_input_required[0]
    assert item.disposition is RotationDDDamageBlockerDisposition.RUNTIME_INPUT_REQUIRED
    assert "lacks exact caller/runtime evidence" in (item.disposition_reason or "")


def test_saved_build_stampede_impact_gaps_remain_grouped_runtime_dependency() -> None:
    blocker = RotationDDDamageCoverageBlocker(
        action_kind=RotationActionKind.SKILL,
        action_name="Stampede",
        reason=(
            "Stampede coefficient 2: reviewed activation anchor impact "
            "requires exact runtime anchor evidence"
        ),
        occurrences=((10.0, 10), (31.0, 31), (46.0, 46)),
    )
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="saved-build-generated",
        total_damage_actions=3,
        resolved_damage_actions=0,
        unresolved_damage_actions=3,
        blockers=(blocker,),
    )

    result = _service().classify(audit)

    assert audit.complete is False
    assert result.actionable == ()
    assert result.parked == ()
    assert len(result.runtime_input_required) == 1
    runtime_dependency = result.runtime_input_required[0]
    assert runtime_dependency.disposition is RotationDDDamageBlockerDisposition.RUNTIME_INPUT_REQUIRED
    assert runtime_dependency.blocker.action_name == "Stampede"
    assert runtime_dependency.blocker.occurrence_count == 3
    assert runtime_dependency.blocker.occurrences == (
        (10.0, 10),
        (31.0, 31),
        (46.0, 46),
    )
    assert "lacks exact caller/runtime evidence" in (
        runtime_dependency.disposition_reason or ""
    )


def test_target_health_snapshot_gap_is_runtime_input_not_engineering_work() -> None:
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="candidate",
        total_damage_actions=1,
        resolved_damage_actions=0,
        unresolved_damage_actions=1,
        blockers=(
            _blocker(
                "Killer's Blade",
                "Killer's Blade: coefficient 1: target-health conditional damage requires an exact runtime snapshot",
            ),
        ),
    )

    result = _service().classify(audit)

    assert result.actionable == ()
    assert result.parked == ()
    assert len(result.runtime_input_required) == 1
    assert result.runtime_input_required[0].disposition is (
        RotationDDDamageBlockerDisposition.RUNTIME_INPUT_REQUIRED
    )


def test_parked_periodic_target_health_timing_gap_remains_evidence_work() -> None:
    audit = RotationDDWholePlanDamageCoverageAudit(
        candidate_id="candidate",
        total_damage_actions=1,
        resolved_damage_actions=0,
        unresolved_damage_actions=1,
        blockers=(
            _blocker(
                "Unnerving Boneyard",
                "Unnerving Boneyard: coefficient 1 periodic target-Health timing is not source-reviewed",
            ),
        ),
    )

    result = _service().classify(audit)

    assert result.actionable == ()
    assert result.runtime_input_required == ()
    assert len(result.parked) == 1
    assert result.parked[0].disposition is RotationDDDamageBlockerDisposition.PARKED_EVIDENCE
