from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)
from services.team_provider_rotation_workload_service import (
    TeamProviderRotationContribution,
    TeamProviderRotationWorkloadService,
    TeamProviderScheduledActionCost,
)
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)
from services.team_provider_workload_explanation_service import (
    TeamProviderWorkloadExplanationService,
)
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadCandidateRejection,
    TeamProviderWorkloadCandidateResult,
)


def _workload(*, applications, recipient, temporal):
    actions = tuple(
        RotationAction(time, 0, RotationActionKind.SKILL, "Provider Skill", "front")
        for time in applications
    )
    plan = RotationPlan("Magrat", "DF Healer", 60.0, actions)
    contribution = TeamProviderRotationContribution(
        plan=plan,
        provider_actions=tuple(
            TeamProviderScheduledActionCost(
                time,
                0,
                gcd_seconds=1.0,
                resource_costs=(("magicka", 2000.0),),
                primary_role_displacement_seconds=0.5,
            )
            for time in applications
        ),
    )
    return TeamProviderRotationWorkloadService().assess_from_coverage(
        alternative_id="healer provider",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_result=recipient,
        temporal_coverage_result=temporal,
        contributions=(contribution,),
    )


def test_describe_exposes_recipient_timeline_gap_and_workload_for_ui():
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("combat_prayer", 6, 1),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement("minor courage", 0.0, 60.0, target_coverage_ratio=0.75),
        applications=(TeamProviderTimedApplication("minor courage", "Magrat", 0.0, 45.0),),
    )

    explanation = TeamProviderWorkloadExplanationService.describe(
        _workload(applications=(0.0,), recipient=recipient, temporal=temporal)
    )

    assert explanation.coverage[0] == (
        "Recipient coverage: 6/12 recipients; 6 still uncovered."
    )
    assert "45/60 seconds (75.0%); target 75.0% met" in explanation.coverage[1]
    assert explanation.coverage[2] == "Uncovered timeline windows: 45-60s."
    assert "1 applications (1/minute)" in explanation.workload[0]
    assert explanation.workload[-1] == "Resource spend: 2000 Magicka."


def test_compare_reports_independent_tradeoffs_without_inventing_winner():
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("provider", 12, 1),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement("minor courage", 0.0, 60.0),
        applications=(TeamProviderTimedApplication("minor courage", "Magrat", 0.0, 60.0),),
    )
    service = TeamProviderRotationWorkloadService()
    baseline = _workload(
        applications=(0.0, 20.0, 40.0), recipient=recipient, temporal=temporal
    )
    candidate = _workload(
        applications=(0.0,), recipient=recipient, temporal=temporal
    )

    explanation = TeamProviderWorkloadExplanationService.compare(
        service.compare(baseline, candidate)
    )

    assert "Candidate uses 2 fewer applications per minute." in explanation.tradeoffs
    assert "Candidate spends 4000 less Magicka." in explanation.tradeoffs
    assert "not a universal winner" in explanation.boundary

    panel = TeamProviderWorkloadExplanationService.render_panel(
        (baseline, candidate),
        comparison=service.compare(baseline, candidate),
    )
    assert "COMPARISON • healer provider → healer provider" in panel
    assert "Candidate spends 4000 less Magicka." in panel


def test_empty_panel_preserves_static_vs_rotation_boundary():
    panel = TeamProviderWorkloadExplanationService.render_panel(())

    assert "No canonical provider rotation workload" in panel
    assert "Static capability availability does not prove" in panel


def test_panel_rejects_comparison_for_hidden_workloads():
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("provider", 12, 1),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement("minor courage", 0.0, 60.0),
        applications=(
            TeamProviderTimedApplication("minor courage", "Magrat", 0.0, 60.0),
        ),
    )
    service = TeamProviderRotationWorkloadService()
    baseline = _workload(
        applications=(0.0, 20.0), recipient=recipient, temporal=temporal
    )
    candidate = _workload(
        applications=(0.0,), recipient=recipient, temporal=temporal
    )

    try:
        TeamProviderWorkloadExplanationService.render_panel(
            (baseline,),
            comparison=service.compare(baseline, candidate),
        )
    except ValueError as exc:
        assert "displayed workloads" in str(exc)
    else:
        raise AssertionError("expected hidden comparison evidence to fail closed")


def test_renders_candidate_attachment_blockers_without_claiming_workload():
    result = TeamProviderWorkloadCandidateResult(
        projections=(),
        rejected=(
            TeamProviderWorkloadCandidateRejection(
                alternative_id="prayer cadence",
                effect_key="minor_berserk",
                blockers=("Magrat / Trial Healer: no exact rotation plan is attached",),
            ),
        ),
    )

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(result)

    assert "PRAYER CADENCE • minor_berserk" in rendered
    assert "Candidate not projected" in rendered
    assert "no exact rotation plan is attached" in rendered
    assert "Provider work:" not in rendered
