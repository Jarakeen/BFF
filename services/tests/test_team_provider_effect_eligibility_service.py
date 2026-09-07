from __future__ import annotations

import pytest

from services.team_provider_effect_eligibility_service import (
    EncounterEligibilityWindow,
    TeamProviderEffectEligibilityRule,
    TeamProviderEffectEligibilityService,
)
from services.team_provider_temporal_coverage_service import TeamProviderTimedApplication


def _window(key, start, end, *categories, targets=()):
    return EncounterEligibilityWindow(
        window_key=key,
        start_seconds=start,
        end_seconds=end,
        categories=tuple(categories),
        target_keys=tuple(targets),
    )


def _app(effect, source, start, duration):
    return TeamProviderTimedApplication(
        effect_key=effect,
        source=source,
        start_seconds=start,
        duration_seconds=duration,
    )


def _lokke_windows():
    return (
        _window(
            "grounded_1",
            0.0,
            60.0,
            "boss_damageable",
            "raid_damage",
            targets=("lokke", "raid"),
        ),
        _window(
            "atro_phase",
            60.0,
            90.0,
            "adds_damageable",
            "raid_damage",
            targets=("atronachs", "raid"),
        ),
        _window(
            "transition_wait",
            90.0,
            95.0,
            "transition_wait",
            targets=("raid",),
        ),
        _window(
            "grounded_2",
            95.0,
            155.0,
            "boss_damageable",
            "raid_damage",
            targets=("lokke", "raid"),
        ),
    )


def test_lokke_boss_offense_uses_only_grounded_damageable_windows():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("boss_damageable",),
            target_keys=("lokke",),
            target_coverage_ratio=0.75,
        ),
        windows=_lokke_windows(),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 45.0),
            _app("major_force", "Healer Horn", 95.0, 45.0),
        ),
    )

    assert result.eligible_intervals == ((0.0, 60.0), (95.0, 155.0))
    assert result.eligible_seconds == pytest.approx(120.0)
    assert result.covered_seconds == pytest.approx(90.0)
    assert result.coverage_ratio == pytest.approx(0.75)
    assert result.target_coverage_met is True


def test_same_lokke_apps_look_worse_against_full_fight_denominator():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("encounter_active",),
            target_coverage_ratio=0.75,
        ),
        windows=(_window("whole_fight", 0.0, 155.0, "encounter_active"),),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 45.0),
            _app("major_force", "Healer Horn", 95.0, 45.0),
        ),
    )

    assert result.eligible_seconds == pytest.approx(155.0)
    assert result.coverage_ratio == pytest.approx(90.0 / 155.0)
    assert result.target_coverage_met is False


def test_general_offensive_support_can_include_boss_and_add_damage_time_but_not_wait():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="powerful_assault",
            eligible_categories=("boss_damageable", "adds_damageable"),
            target_coverage_ratio=0.75,
        ),
        windows=_lokke_windows(),
        applications=(
            _app("powerful_assault", "Healer PA", 0.0, 60.0),
            _app("powerful_assault", "Healer PA", 60.0, 30.0),
            _app("powerful_assault", "Healer PA", 95.0, 30.0),
        ),
    )

    assert result.eligible_intervals == ((0.0, 90.0), (95.0, 155.0))
    assert result.eligible_seconds == pytest.approx(150.0)
    assert result.covered_seconds == pytest.approx(120.0)
    assert result.coverage_ratio == pytest.approx(0.80)
    assert result.target_coverage_met is True


def test_lokke_healing_support_keeps_intense_flight_phase_in_denominator():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="healing_support",
            eligible_categories=("raid_damage",),
            target_keys=("raid",),
            target_coverage_ratio=0.90,
        ),
        windows=_lokke_windows(),
        applications=(
            _app("healing_support", "Healer A", 0.0, 90.0),
            _app("healing_support", "Healer B", 95.0, 60.0),
        ),
    )

    assert result.eligible_intervals == ((0.0, 90.0), (95.0, 155.0))
    assert result.eligible_seconds == pytest.approx(150.0)
    assert result.covered_seconds == pytest.approx(150.0)
    assert result.coverage_ratio == pytest.approx(1.0)
    assert result.target_coverage_met is True


def test_targeted_rule_does_not_treat_unknown_target_identity_as_eligible():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("boss_damageable",),
            target_keys=("lokke",),
        ),
        windows=(
            _window("known_lokke", 0.0, 20.0, "boss_damageable", targets=("lokke",)),
            _window("unknown_boss", 20.0, 40.0, "boss_damageable"),
        ),
        applications=(_app("major_force", "Horn", 0.0, 40.0),),
    )

    assert result.eligible_intervals == ((0.0, 20.0),)
    assert result.eligible_seconds == pytest.approx(20.0)
    assert result.coverage_ratio == pytest.approx(1.0)


def test_overlapping_eligibility_windows_are_not_double_counted():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="major_slayer",
            eligible_categories=("boss_damageable",),
        ),
        windows=(
            _window("a", 0.0, 30.0, "boss_damageable"),
            _window("b", 20.0, 50.0, "boss_damageable"),
        ),
        applications=(_app("major_slayer", "RO", 0.0, 50.0),),
    )

    assert result.eligible_intervals == ((0.0, 50.0),)
    assert result.eligible_seconds == pytest.approx(50.0)
    assert result.covered_seconds == pytest.approx(50.0)


def test_application_time_outside_useful_window_is_reported_not_rewarded():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("boss_damageable",),
            target_keys=("lokke",),
        ),
        windows=_lokke_windows(),
        applications=(
            _app("major_force", "Badly Timed Horn", 55.0, 20.0),
        ),
    )

    assert result.covered_seconds == pytest.approx(5.0)
    assert result.application_seconds_outside_eligible_windows == pytest.approx(15.0)


def test_no_eligible_window_is_not_reported_as_success():
    result = TeamProviderEffectEligibilityService.evaluate(
        TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("boss_damageable",),
            target_keys=("lokke",),
        ),
        windows=(_window("wait", 0.0, 10.0, "transition_wait", targets=("raid",)),),
        applications=(_app("major_force", "Horn", 0.0, 10.0),),
    )

    assert result.eligible_seconds == pytest.approx(0.0)
    assert result.coverage_ratio == pytest.approx(0.0)
    assert result.target_coverage_met is False
