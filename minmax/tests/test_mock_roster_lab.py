from minmax.coverage_classification import CoverageClassification
from minmax.mock_roster_lab import MockRosterLab


def test_scenario_library_contains_core_phase5_cases():
    keys = MockRosterLab.scenario_keys()

    assert "balanced12" in keys
    assert "twelve_healers" in keys
    assert "twelve_dds" in keys
    assert "conflict" in keys
    assert "bad_uptime" in keys


def test_twelve_healer_roster_is_a_real_evaluation_case():
    lab = MockRosterLab()
    scenario = lab.scenario("twelve_healers")

    assert len(scenario.players) == 12
    assert all(player.role.value == "healer" for player in scenario.players)

    evaluation = lab.evaluate(scenario)

    assert evaluation.classifications
    assert evaluation.is_fully_covered
    assert all(
        result.classification in {
            CoverageClassification.REDUNDANT,
            CoverageClassification.COVERED,
        }
        for result in evaluation.classifications
    )


def test_missing_support_is_reported_by_no_healer_roster():
    lab = MockRosterLab()
    evaluation = lab.evaluate(lab.scenario("no_healers"))

    assert any(
        result.classification == CoverageClassification.MISSING
        for result in evaluation.classifications
    )


def test_bad_uptime_is_insufficient_not_missing():
    lab = MockRosterLab()
    evaluation = lab.evaluate(lab.scenario("bad_uptime"))

    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.valid_provider_count == 0


def test_conflict_scenario_reaches_phase4_conflict_classification():
    lab = MockRosterLab()
    evaluation = lab.evaluate(lab.scenario("conflict"))

    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.CONFLICT
    assert not evaluation.is_fully_covered


def test_mock_lab_never_needs_production_roster_data():
    lab = MockRosterLab()
    scenario = lab.scenario("minimal")

    capabilities = lab.capabilities_for(scenario)

    assert capabilities
    assert all(
        provider.effect.source == "Phase 5 Mock Roster"
        for providers in capabilities.values()
        for provider in providers
    )
