from __future__ import annotations

import pytest

from services.rotation_support_refresh_cadence_service import (
    RotationSupportRefreshCadenceService,
)
from services.team_provider_uptime_policy_service import TeamProviderUptimePolicy


def _policy(*, target: float, theoretical: float | None = None) -> TeamProviderUptimePolicy:
    return TeamProviderUptimePolicy(
        effect_key="major_slayer",
        target_ratio=target,
        theoretical_max_ratio=theoretical,
        encounter_key="example_trial",
        source="explicit encounter strategy",
    )


def test_generates_full_coverage_and_target_floor_from_effective_duration() -> None:
    result = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.90),
        source_skill_id="combat_prayer",
        effective_duration_seconds=10.0,
    )

    assert result.effect_key == "major_slayer"
    assert result.source_skill_id == "combat_prayer"
    assert result.unresolved == ()
    assert [candidate.candidate_key for candidate in result.candidates] == [
        "full_coverage",
        "target_floor",
    ]

    full, target = result.candidates
    assert full.recast_interval_seconds == pytest.approx(10.0)
    assert full.projected_steady_state_uptime_ratio == pytest.approx(1.0)
    assert target.recast_interval_seconds == pytest.approx(10.0 / 0.90)
    assert target.projected_steady_state_uptime_ratio == pytest.approx(0.90)


def test_build_effective_duration_changes_generated_cadence() -> None:
    base = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.80),
        source_skill_id="support_skill",
        effective_duration_seconds=10.0,
    )
    extended = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.80),
        source_skill_id="support_skill",
        effective_duration_seconds=26.0,
    )

    assert base.candidates[0].recast_interval_seconds == pytest.approx(10.0)
    assert extended.candidates[0].recast_interval_seconds == pytest.approx(26.0)
    assert base.candidates[1].recast_interval_seconds == pytest.approx(12.5)
    assert extended.candidates[1].recast_interval_seconds == pytest.approx(32.5)


def test_one_hundred_percent_target_deduplicates_identical_cadence() -> None:
    result = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=1.0),
        source_skill_id="support_skill",
        effective_duration_seconds=12.0,
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].candidate_key == "full_coverage"
    assert result.candidates[0].recast_interval_seconds == pytest.approx(12.0)


def test_zero_target_does_not_invent_a_maintenance_cadence() -> None:
    result = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.0),
        source_skill_id="support_skill",
        effective_duration_seconds=12.0,
    )

    assert result.candidates == ()
    assert result.unresolved == ()


def test_missing_effective_duration_is_unresolved_not_guessed() -> None:
    result = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.90),
        source_skill_id="support_skill",
        effective_duration_seconds=None,
    )

    assert result.candidates == ()
    assert result.unresolved
    assert "not guessed" in result.unresolved[0]


def test_cycle_limited_effect_requires_runtime_evidence_instead_of_global_cadence() -> None:
    result = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.30, theoretical=0.318),
        source_skill_id="wall_of_elements",
        effective_duration_seconds=10.0,
    )

    assert result.candidates == ()
    assert result.unresolved
    assert "encounter/runtime cycle evidence" in result.unresolved[0]


def test_skill_identity_is_normalized_semantically_not_numeric() -> None:
    result = RotationSupportRefreshCadenceService.derive(
        policy=_policy(target=0.90),
        source_skill_id="Combat Prayer",
        effective_duration_seconds=10.0,
    )

    assert result.source_skill_id == "combat_prayer"
    assert all(candidate.source_skill_id == "combat_prayer" for candidate in result.candidates)


@pytest.mark.parametrize("duration", [0.0, -1.0])
def test_nonpositive_effective_duration_is_rejected(duration: float) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        RotationSupportRefreshCadenceService.derive(
            policy=_policy(target=0.90),
            source_skill_id="support_skill",
            effective_duration_seconds=duration,
        )
