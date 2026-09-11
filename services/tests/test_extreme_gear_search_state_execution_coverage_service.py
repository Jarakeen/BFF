from services.extreme_gear_search_state_execution_coverage_service import (
    ExtremeGearSearchStateExecutionCoverageService,
)
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule


def test_every_reviewed_search_state_rule_has_execution_coverage():
    report = ExtremeGearSearchStateExecutionCoverageService.build()

    assert report.denominator_proven is True
    assert report.unresolved == ()
    assert {row.rule for row in report.rows} == set(ExtremeGearSearchStateRule)
    assert all(row.executable for row in report.rows)


def test_execution_coverage_names_the_expected_owner_layers():
    report = ExtremeGearSearchStateExecutionCoverageService.build()
    by_rule = {row.rule: row for row in report.rows}

    assert any(
        "ExtremeGearBarAccessService" in value
        for value in by_rule[ExtremeGearSearchStateRule.ONE_BAR_ONLY].execution_surfaces
    )
    assert any(
        "RotationRuntimeBarProvenanceService" in value
        for value in by_rule[ExtremeGearSearchStateRule.ONE_BAR_ONLY].execution_surfaces
    )
    assert any(
        "GearSetEffectService" in value
        for value in by_rule[
            ExtremeGearSearchStateRule.SUPPRESSES_OTHER_SET_BONUSES
        ].execution_surfaces
    )
    assert any(
        "ExtremeTwiceBornMundusStructuralStatEvaluator" in value
        for value in by_rule[ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS].execution_surfaces
    )
