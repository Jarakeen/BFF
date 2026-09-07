from __future__ import annotations

import pytest

from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)


def _app(effect, source, start, duration):
    return TeamProviderTimedApplication(
        effect_key=effect,
        source=source,
        start_seconds=start,
        duration_seconds=duration,
    )


def _req(effect="major_force", start=0.0, end=20.0, minimum_distinct_sources=1):
    return TeamProviderTemporalRequirement(
        effect_key=effect,
        start_seconds=start,
        end_seconds=end,
        label="burn phase",
        minimum_distinct_sources=minimum_distinct_sources,
    )


def test_staggered_same_named_buff_extends_full_required_window():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(),
        applications=(
            _app("Major Force", "Tank Horn", 0.0, 10.0),
            _app("major-force", "Healer Horn", 10.0, 10.0),
        ),
    )

    assert result.full_window_covered is True
    assert result.full_requirement_met is True
    assert result.coverage_ratio == pytest.approx(1.0)
    assert result.covered_seconds == pytest.approx(20.0)
    assert result.uncovered_seconds == pytest.approx(0.0)
    assert result.simultaneous_overlap_seconds == pytest.approx(0.0)
    assert result.active_sources == ("Tank Horn", "Healer Horn")


def test_simultaneous_duplicate_does_not_extend_temporal_coverage():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 10.0),
            _app("major_force", "Healer Horn", 0.0, 10.0),
        ),
    )

    assert result.full_window_covered is False
    assert result.coverage_ratio == pytest.approx(0.5)
    assert result.covered_seconds == pytest.approx(10.0)
    assert result.uncovered_intervals == ((10.0, 20.0),)
    assert result.simultaneous_overlap_seconds == pytest.approx(10.0)


def test_partial_stagger_reports_middle_gap_explicitly():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 8.0),
            _app("major_force", "Healer Horn", 12.0, 8.0),
        ),
    )

    assert result.covered_seconds == pytest.approx(16.0)
    assert result.uncovered_seconds == pytest.approx(4.0)
    assert result.uncovered_intervals == ((8.0, 12.0),)


def test_one_carrier_can_refresh_repeatedly_when_runtime_schedule_supports_it():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(effect="support_buff", end=24.0),
        applications=(
            _app("support_buff", "Healer A", 0.0, 8.0),
            _app("support_buff", "Healer A", 8.0, 8.0),
            _app("support_buff", "Healer A", 16.0, 8.0),
        ),
    )

    assert result.full_window_covered is True
    assert result.full_requirement_met is True
    assert result.active_sources == ("Healer A",)


def test_strategy_can_require_two_distinct_horn_carriers_even_when_one_source_covers_time():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(end=20.0, minimum_distinct_sources=2),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 10.0),
            _app("major_force", "Tank Horn", 10.0, 10.0),
        ),
    )

    assert result.full_window_covered is True
    assert result.distinct_source_count == 1
    assert result.distinct_source_requirement_met is False
    assert result.full_requirement_met is False


def test_tank_and_healer_stagger_can_satisfy_two_carrier_strategy_requirement():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(end=20.0, minimum_distinct_sources=2),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 10.0),
            _app("major_force", "Healer Horn", 10.0, 10.0),
        ),
    )

    assert result.full_window_covered is True
    assert result.distinct_source_count == 2
    assert result.distinct_source_requirement_met is True
    assert result.full_requirement_met is True


def test_two_healers_can_overlap_short_support_buff_without_overlap_being_auto_rejected():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(effect="combat_prayer_effect", end=12.0),
        applications=(
            _app("combat_prayer_effect", "Healer A Combat Prayer", 0.0, 8.0),
            _app("combat_prayer_effect", "Healer B Combat Prayer", 4.0, 8.0),
        ),
    )

    assert result.full_window_covered is True
    assert result.simultaneous_overlap_seconds == pytest.approx(4.0)
    assert result.uncovered_seconds == pytest.approx(0.0)


def test_unrelated_named_effect_is_ignored():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(),
        applications=(
            _app("minor_force", "Unrelated", 0.0, 20.0),
        ),
    )

    assert result.covered_seconds == pytest.approx(0.0)
    assert result.uncovered_intervals == ((0.0, 20.0),)
    assert result.active_sources == ()


def test_application_is_clipped_to_required_phase_window():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(start=10.0, end=20.0),
        applications=(
            _app("major_force", "Early Horn", 5.0, 10.0),
            _app("major_force", "Late Horn", 15.0, 10.0),
        ),
    )

    assert result.covered_intervals == ((10.0, 20.0),)
    assert result.covered_seconds == pytest.approx(10.0)
    assert result.simultaneous_overlap_seconds == pytest.approx(0.0)


def test_overlap_chain_merges_into_one_continuous_covered_interval():
    result = TeamProviderTemporalCoverageService.evaluate(
        _req(end=18.0),
        applications=(
            _app("major_force", "A", 0.0, 8.0),
            _app("major_force", "B", 6.0, 8.0),
            _app("major_force", "C", 12.0, 6.0),
        ),
    )

    assert result.covered_intervals == ((0.0, 18.0),)
    assert result.full_window_covered is True
    assert result.simultaneous_overlap_seconds == pytest.approx(4.0)


@pytest.mark.parametrize(
    "application",
    [
        lambda: TeamProviderTimedApplication("", "source", 0.0, 1.0),
        lambda: TeamProviderTimedApplication("buff", "", 0.0, 1.0),
        lambda: TeamProviderTimedApplication("buff", "source", -1.0, 1.0),
        lambda: TeamProviderTimedApplication("buff", "source", 0.0, 0.0),
    ],
)
def test_invalid_timed_application_is_rejected(application):
    with pytest.raises(ValueError):
        application()


@pytest.mark.parametrize(
    "requirement",
    [
        lambda: TeamProviderTemporalRequirement("", 0.0, 1.0),
        lambda: TeamProviderTemporalRequirement("buff", -1.0, 1.0),
        lambda: TeamProviderTemporalRequirement("buff", 1.0, 1.0),
        lambda: TeamProviderTemporalRequirement("buff", 2.0, 1.0),
        lambda: TeamProviderTemporalRequirement("buff", 0.0, 1.0, minimum_distinct_sources=0),
    ],
)
def test_invalid_temporal_requirement_is_rejected(requirement):
    with pytest.raises(ValueError):
        requirement()
