import pytest

from services.team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)


def test_banner_single_instance_covers_user_plus_five_only():
    profile = TeamProviderCoverageProfile(
        provider_key="banner",
        targets_per_application=6,
        max_applications_per_cycle=1,
        application_label="banner",
    )

    result = TeamProviderCoverageService.evaluate(profile, required_recipients=12)

    assert result.applications_needed == 2
    assert result.applications_available == 1
    assert result.applications_used == 1
    assert result.covered_recipients == 6
    assert result.uncovered_recipients == 6
    assert result.fully_covered is False
    assert result.coverage_ratio == pytest.approx(0.5)


def test_roaring_opportunist_two_heavy_attacks_cover_twelve():
    profile = TeamProviderCoverageProfile(
        provider_key="roaring_opportunist",
        targets_per_application=6,
        max_applications_per_cycle=2,
        application_label="heavy attack",
    )

    result = TeamProviderCoverageService.evaluate(profile, required_recipients=12)

    assert result.applications_needed == 2
    assert result.applications_used == 2
    assert result.covered_recipients == 12
    assert result.uncovered_recipients == 0
    assert result.fully_covered is True


def test_powerful_assault_two_vigors_cover_twelve():
    profile = TeamProviderCoverageProfile(
        provider_key="powerful_assault",
        targets_per_application=6,
        max_applications_per_cycle=2,
        application_label="Vigor cast",
    )

    result = TeamProviderCoverageService.evaluate(profile, required_recipients=12)

    assert result.applications_needed == 2
    assert result.applications_used == 2
    assert result.covered_recipients == 12
    assert result.fully_covered is True


def test_required_recipient_count_can_be_smaller_than_full_trial_group():
    profile = TeamProviderCoverageProfile(
        provider_key="six_target_support",
        targets_per_application=6,
        max_applications_per_cycle=1,
    )

    result = TeamProviderCoverageService.evaluate(profile, required_recipients=4)

    assert result.applications_needed == 1
    assert result.covered_recipients == 4
    assert result.uncovered_recipients == 0


def test_repeatable_provider_without_explicit_cycle_cap_scales_to_required_recipients():
    profile = TeamProviderCoverageProfile(
        provider_key="repeatable_six_target_support",
        targets_per_application=6,
        max_applications_per_cycle=None,
    )

    result = TeamProviderCoverageService.evaluate(profile, required_recipients=12)

    assert result.applications_needed == 2
    assert result.applications_available == 2
    assert result.covered_recipients == 12


def test_two_single_instance_six_target_providers_can_cover_twelve_in_capacity_upper_bound():
    profiles = (
        TeamProviderCoverageProfile(
            provider_key="banner_a",
            targets_per_application=6,
            max_applications_per_cycle=1,
        ),
        TeamProviderCoverageProfile(
            provider_key="banner_b",
            targets_per_application=6,
            max_applications_per_cycle=1,
        ),
    )

    result = TeamProviderCoverageService.combine(profiles, required_recipients=12)

    assert result.covered_recipients == 12
    assert result.uncovered_recipients == 0
    assert result.fully_covered is True


def test_zero_required_recipients_is_vacuously_covered():
    profile = TeamProviderCoverageProfile(
        provider_key="anything",
        targets_per_application=6,
        max_applications_per_cycle=1,
    )

    result = TeamProviderCoverageService.evaluate(profile, required_recipients=0)

    assert result.fully_covered is True
    assert result.coverage_ratio == pytest.approx(1.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"provider_key": "", "targets_per_application": 6},
        {"provider_key": "bad", "targets_per_application": 0},
        {
            "provider_key": "bad",
            "targets_per_application": 6,
            "max_applications_per_cycle": 0,
        },
    ],
)
def test_invalid_coverage_profiles_are_rejected(kwargs):
    with pytest.raises(ValueError):
        TeamProviderCoverageProfile(**kwargs)


def test_negative_required_recipient_count_is_rejected():
    profile = TeamProviderCoverageProfile(
        provider_key="anything",
        targets_per_application=6,
    )

    with pytest.raises(ValueError, match="required_recipients"):
        TeamProviderCoverageService.evaluate(profile, required_recipients=-1)
