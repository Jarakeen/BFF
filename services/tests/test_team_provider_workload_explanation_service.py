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
