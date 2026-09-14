import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.btv_benchmark_evidence_service import (
    BTVBenchmarkEvidenceService,
    BTVBenchmarkObservation,
)
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


def _workload(*, alternative_id="slayer plan", duration=56.0):
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("major_slayer", 12, 1),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement(
            "major_slayer",
            0.0,
            100.0,
            target_coverage_ratio=0.90,
        ),
        applications=(
            TeamProviderTimedApplication(
                "major_slayer",
                "healer",
                0.0,
                duration,
            ),
        ),
    )
    plan = RotationPlan(
        "Magrat",
        "DF Healer",
        100.0,
        (RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider", "front"),),
    )
    contribution = TeamProviderRotationContribution(
        plan=plan,
        provider_actions=(
            TeamProviderScheduledActionCost(
                0.0,
                0,
                gcd_seconds=1.0,
                resource_costs=(),
                ultimate_cost=0.0,
                primary_role_displacement_seconds=0.0,
            ),
        ),
    )
    return TeamProviderRotationWorkloadService().assess_from_coverage(
        alternative_id=alternative_id,
        effect_key="major_slayer",
        duration_seconds=100.0,
        recipient_coverage_result=recipient,
        temporal_coverage_result=temporal,
        contributions=(contribution,),
    )


def _observation():
    return BTVBenchmarkObservation(
        encounter_key="lokke_hm",
        encounter_label="Lokkestiiz hard mode",
        effect_key="major_slayer",
        page="insights",
        observed_ratio=0.56,
        target_ratio=0.90,
        reference_average_ratio=None,
        theoretical_max_ratio=None,
        contribution_percent=None,
        player_role=None,
        source_file="Screenshot 2026-09-07 170229.png",
        source="BTVTools screenshots supplied by user",
    )


def test_render_panel_surfaces_scoped_btv_calibration_without_promoting_it_to_mechanics():
    workload = _workload()
    assessment = BTVBenchmarkEvidenceService.assess_temporal_result(
        _observation(),
        workload.temporal_coverage_result,
    )

    rendered = TeamProviderWorkloadExplanationService.render_panel(
        (workload,),
        benchmark_assessments={workload.alternative_id: assessment},
    )

    assert "BTV benchmark calibration:" in rendered
    assert "Lokkestiiz hard mode • insights • Screenshot 2026-09-07 170229.png" in rendered
    assert "34.0 percentage points below the scoped BTV target 90.0%" in rendered
    assert "Unresolved calibration:" in rendered
    assert "denominator bases are not both known and equal" in rendered
    assert "does not redefine canonical ESO mechanics" in rendered


def test_render_panel_rejects_stale_benchmark_assessment_from_another_timeline():
    displayed = _workload(duration=56.0)
    stale = _workload(duration=80.0)
    assessment = BTVBenchmarkEvidenceService.assess_temporal_result(
        _observation(),
        stale.temporal_coverage_result,
    )

    with pytest.raises(ValueError, match="does not match the displayed workload timeline"):
        TeamProviderWorkloadExplanationService.render_panel(
            (displayed,),
            benchmark_assessments={displayed.alternative_id: assessment},
        )


def test_render_panel_rejects_calibration_for_hidden_alternative():
    workload = _workload()
    assessment = BTVBenchmarkEvidenceService.assess_temporal_result(
        _observation(),
        workload.temporal_coverage_result,
    )

    with pytest.raises(ValueError, match="hidden workload alternatives"):
        TeamProviderWorkloadExplanationService.render_panel(
            (workload,),
            benchmark_assessments={"not displayed": assessment},
        )
