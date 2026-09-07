from __future__ import annotations

import pytest

from services.team_provider_uptime_policy_service import (
    TeamProviderUptimePolicy,
    TeamProviderUptimePolicyService,
)


def test_benchmark_target_is_scoped_and_keeps_provenance():
    policy = TeamProviderUptimePolicy(
        effect_key="major_slayer",
        target_ratio=0.90,
        encounter_key="lokke_hm_example",
        source="BTVTools screenshot benchmark",
        note="example benchmark from one Lokke hard mode fight",
    )

    result = TeamProviderUptimePolicyService.assess(policy, observed_ratio=0.56)

    assert policy.encounter_key == "lokke_hm_example"
    assert policy.source == "BTVTools screenshot benchmark"
    assert result.target_met is False
    assert result.shortfall_ratio == pytest.approx(0.34)


def test_powerful_assault_example_can_target_ninety_five_percent_without_making_it_global():
    policy = TeamProviderUptimePolicy(
        effect_key="powerful_assault",
        target_ratio=0.95,
        encounter_key="lokke_hm_example",
        source="BTVTools screenshot benchmark",
    )

    result = TeamProviderUptimePolicyService.assess(policy, observed_ratio=0.85)

    assert result.target_met is False
    assert result.shortfall_percent == pytest.approx(10.0)


def test_major_vulnerability_example_uses_its_own_lower_target():
    policy = TeamProviderUptimePolicy(
        effect_key="major_vulnerability",
        target_ratio=0.56,
        encounter_key="lokke_hm_example",
        source="BTVTools screenshot benchmark",
    )

    result = TeamProviderUptimePolicyService.assess(policy, observed_ratio=0.383)

    assert result.target_met is False
    assert result.shortfall_ratio == pytest.approx(0.177)


def test_theoretical_maximum_is_distinct_from_target_and_reports_headroom():
    policy = TeamProviderUptimePolicy(
        effect_key="off_balance",
        target_ratio=0.30,
        encounter_key="lokke_hm_example",
        theoretical_max_ratio=0.318,
        source="BTVTools screenshot theoretical cycle note",
        note="example showed theoretical max about 31.8 percent from a 7s/22s cycle",
    )

    result = TeamProviderUptimePolicyService.assess(policy, observed_ratio=0.066)

    assert result.target_met is False
    assert result.shortfall_ratio == pytest.approx(0.234)
    assert result.theoretical_headroom_ratio == pytest.approx(0.252)


def test_impossible_target_above_theoretical_maximum_is_rejected_not_clamped():
    with pytest.raises(ValueError, match="cannot exceed"):
        TeamProviderUptimePolicy(
            effect_key="off_balance",
            target_ratio=0.50,
            theoretical_max_ratio=0.318,
            source="bad fixture",
        )


@pytest.mark.parametrize("target", [-0.01, 1.01])
def test_invalid_target_ratio_is_rejected(target):
    with pytest.raises(ValueError, match="target_ratio"):
        TeamProviderUptimePolicy(
            effect_key="major_slayer",
            target_ratio=target,
            source="test",
        )


def test_same_effect_can_have_different_targets_in_different_encounters():
    lokke = TeamProviderUptimePolicy(
        effect_key="major_slayer",
        target_ratio=0.90,
        encounter_key="lokke_hm_example",
        source="benchmark A",
    )
    another = TeamProviderUptimePolicy(
        effect_key="major_slayer",
        target_ratio=0.75,
        encounter_key="different_encounter_strategy",
        source="strategy B",
    )

    assert lokke.target_ratio != another.target_ratio
    assert lokke.encounter_key != another.encounter_key
