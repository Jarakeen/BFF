from __future__ import annotations

import pytest

from services.team_provider_effect_eligibility_service import (
    EncounterEligibilityWindow,
    TeamProviderEffectEligibilityRule,
)
from services.team_provider_effect_uptime_assessment_service import (
    TeamProviderEffectUptimeAssessmentService,
)
from services.team_provider_temporal_coverage_service import TeamProviderTimedApplication
from services.team_provider_uptime_policy_service import TeamProviderUptimePolicy


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
        _window("grounded_1", 0.0, 60.0, "boss_damageable", "raid_damage", targets=("lokke", "raid")),
        _window("atro_phase", 60.0, 90.0, "adds_damageable", "raid_damage", targets=("atronachs", "raid")),
        _window("transition_wait", 90.0, 95.0, "transition_wait", targets=("raid",)),
        _window("grounded_2", 95.0, 155.0, "boss_damageable", "raid_damage", targets=("lokke", "raid")),
    )


def test_major_force_policy_is_assessed_against_lokke_damageable_time():
    result = TeamProviderEffectUptimeAssessmentService.assess(
        TeamProviderUptimePolicy(
            effect_key="major_force",
            target_ratio=0.75,
            encounter_key="lokke_hm",
            source="strategy",
        ),
        eligibility_rule=TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("boss_damageable",),
            target_keys=("lokke",),
        ),
        windows=_lokke_windows(),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 45.0),
            _app("major_force", "Healer Horn", 95.0, 45.0),
        ),
    )

    assert result.eligibility.eligible_seconds == pytest.approx(120.0)
    assert result.policy_assessment.observed_ratio == pytest.approx(0.75)
    assert result.target_met is True


def test_same_major_force_schedule_fails_a_full_encounter_75_percent_target():
    result = TeamProviderEffectUptimeAssessmentService.assess(
        TeamProviderUptimePolicy(
            effect_key="major_force",
            target_ratio=0.75,
            encounter_key="lokke_hm",
            source="strategy",
        ),
        eligibility_rule=TeamProviderEffectEligibilityRule(
            effect_key="major_force",
            eligible_categories=("encounter_active",),
        ),
        windows=(_window("whole_fight", 0.0, 155.0, "encounter_active"),),
        applications=(
            _app("major_force", "Tank Horn", 0.0, 45.0),
            _app("major_force", "Healer Horn", 95.0, 45.0),
        ),
    )

    assert result.policy_assessment.observed_ratio == pytest.approx(90.0 / 155.0)
    assert result.target_met is False


def test_healing_policy_can_include_lokke_flight_phase_raid_damage():
    result = TeamProviderEffectUptimeAssessmentService.assess(
        TeamProviderUptimePolicy(
            effect_key="healing_support",
            target_ratio=0.90,
            encounter_key="lokke_hm",
            source="strategy",
        ),
        eligibility_rule=TeamProviderEffectEligibilityRule(
            effect_key="healing_support",
            eligible_categories=("raid_damage",),
            target_keys=("raid",),
        ),
        windows=_lokke_windows(),
        applications=(
            _app("healing_support", "Healer A", 0.0, 90.0),
            _app("healing_support", "Healer B", 95.0, 60.0),
        ),
    )

    assert result.eligibility.eligible_intervals == ((0.0, 90.0), (95.0, 155.0))
    assert result.eligibility.eligible_seconds == pytest.approx(150.0)
    assert result.policy_assessment.observed_ratio == pytest.approx(1.0)
    assert result.target_met is True


def test_policy_and_eligibility_effect_must_match():
    with pytest.raises(ValueError, match="same effect"):
        TeamProviderEffectUptimeAssessmentService.assess(
            TeamProviderUptimePolicy(
                effect_key="major_force",
                target_ratio=0.75,
                source="strategy",
            ),
            eligibility_rule=TeamProviderEffectEligibilityRule(
                effect_key="major_slayer",
                eligible_categories=("boss_damageable",),
            ),
            windows=(_window("boss", 0.0, 10.0, "boss_damageable"),),
            applications=(),
        )


def test_missing_eligible_windows_stays_unresolved_instead_of_zero_uptime():
    with pytest.raises(ValueError, match="eligible encounter window"):
        TeamProviderEffectUptimeAssessmentService.assess(
            TeamProviderUptimePolicy(
                effect_key="major_force",
                target_ratio=0.75,
                source="strategy",
            ),
            eligibility_rule=TeamProviderEffectEligibilityRule(
                effect_key="major_force",
                eligible_categories=("boss_damageable",),
                target_keys=("lokke",),
            ),
            windows=(_window("wait", 0.0, 10.0, "transition_wait", targets=("raid",)),),
            applications=(),
        )
