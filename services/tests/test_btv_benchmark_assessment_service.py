from pathlib import Path

import pytest

from services.btv_benchmark_assessment_service import BTVBenchmarkAssessmentService
from services.btv_benchmark_evidence_service import (
    BTVBenchmarkEvidenceService,
    BTVBenchmarkObservation,
    UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME,
)
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)


_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "encounter_research"
    / "btv_benchmarks"
    / "lokke_hm_20260907.json"
)


def _temporal_result(
    effect_key: str,
    *,
    target_ratio: float,
    applications: tuple[TeamProviderTimedApplication, ...],
):
    requirement = TeamProviderTemporalRequirement(
        effect_key=effect_key,
        start_seconds=0.0,
        end_seconds=100.0,
        target_coverage_ratio=target_ratio,
    )
    return TeamProviderTemporalCoverageService.evaluate(
        requirement,
        applications=applications,
    )


def test_selects_group_insights_target_without_using_player_scoped_buff_row():
    corpus = BTVBenchmarkEvidenceService.load(_FIXTURE)

    row = BTVBenchmarkAssessmentService.select_target_observation(
        corpus,
        effect_key="major_slayer",
    )

    assert row is not None
    assert row.page == "insights"
    assert row.player_role is None
    assert row.target_ratio == pytest.approx(0.90)
    assert row.observed_ratio == pytest.approx(0.56)


def test_temporal_assessment_reports_target_shortfall_gaps_and_overlap():
    corpus = BTVBenchmarkEvidenceService.load(_FIXTURE)
    row = BTVBenchmarkAssessmentService.select_target_observation(
        corpus,
        effect_key="major_berserk",
    )
    assert row is not None

    result = _temporal_result(
        "major_berserk",
        target_ratio=row.target_ratio,
        applications=(
            TeamProviderTimedApplication(
                effect_key="major_berserk",
                source="provider_a",
                start_seconds=0.0,
                duration_seconds=40.0,
            ),
            TeamProviderTimedApplication(
                effect_key="major_berserk",
                source="provider_b",
                start_seconds=35.0,
                duration_seconds=40.0,
            ),
        ),
    )

    assessment = BTVBenchmarkAssessmentService.assess_temporal_result(row, result)

    assert result.coverage_ratio == pytest.approx(0.75)
    assert result.uncovered_intervals == ((75.0, 100.0),)
    assert result.simultaneous_overlap_seconds == pytest.approx(5.0)
    assert assessment.target_met is False
    assert any("21.0 percentage points below" in line for line in assessment.feedback)
    assert any("75.0-100.0s" in line for line in assessment.feedback)
    assert any("overlap for 5.0s" in line for line in assessment.feedback)
    assert assessment.benchmark_observed_comparison_allowed is False
    assert any("denominator bases" in line for line in assessment.unresolved)


def test_temporal_assessment_can_compare_observed_when_denominator_is_proven_equal():
    row = BTVBenchmarkObservation(
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
        source_file="reviewed.png",
        source="BTVTools screenshots supplied by user",
        uptime_denominator_basis=UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME,
    )
    result = _temporal_result(
        "major_slayer",
        target_ratio=0.90,
        applications=(
            TeamProviderTimedApplication(
                effect_key="major_slayer",
                source="provider",
                start_seconds=0.0,
                duration_seconds=80.0,
            ),
        ),
    )

    assessment = BTVBenchmarkAssessmentService.assess_temporal_result(
        row,
        result,
        temporal_uptime_denominator_basis=UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME,
    )

    assert assessment.benchmark_observed_comparison_allowed is True
    assert assessment.benchmark_observed_delta_ratio == pytest.approx(0.24)
    assert any("24.0 percentage points above" in line for line in assessment.feedback)


def test_off_balance_fixture_stays_ceiling_only_without_inventing_target():
    corpus = BTVBenchmarkEvidenceService.load(_FIXTURE)
    rows = corpus.find(effect_key="off_balance", page="insights")
    assert len(rows) == 1
    row = rows[0]
    assert row.target_ratio is None
    assert row.theoretical_max_ratio == pytest.approx(0.318)

    result = _temporal_result(
        "off_balance",
        target_ratio=0.25,
        applications=(
            TeamProviderTimedApplication(
                effect_key="off_balance",
                source="provider",
                start_seconds=0.0,
                duration_seconds=25.0,
            ),
        ),
    )
    assessment = BTVBenchmarkAssessmentService.assess_temporal_result(row, result)

    assert assessment.target_met is None
    assert any("provides no target" in line for line in assessment.feedback)
    assert not any("below the scoped BTV target" in line for line in assessment.feedback)


def test_benchmark_row_rejects_target_above_theoretical_maximum():
    with pytest.raises(ValueError, match="target_ratio cannot exceed theoretical_max_ratio"):
        BTVBenchmarkObservation(
            encounter_key="example",
            encounter_label="Example",
            effect_key="example_effect",
            page="insights",
            observed_ratio=0.40,
            target_ratio=0.90,
            reference_average_ratio=None,
            theoretical_max_ratio=0.80,
            contribution_percent=None,
            player_role=None,
            source_file="example.png",
            source="reviewed benchmark",
        )
