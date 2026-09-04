import pytest

from minmax.rotation_maintenance_readiness import assess_rotation_maintenance_readiness
from minmax.rotation_timing_eligibility import eligibility_from_maintenance_readiness
from minmax.saved_build_maintenance_candidates import SavedBuildMaintenanceCandidate


def _candidate() -> SavedBuildMaintenanceCandidate:
    return SavedBuildMaintenanceCandidate(
        bar="front",
        slot=4,
        skill_name="Illustrious Healing",
        duration_seconds=15.0,
        evidence_sources=("canonical effect",),
    )


def test_initial_maintenance_cast_is_timing_ready() -> None:
    readiness = assess_rotation_maintenance_readiness(
        candidate=_candidate(),
        decision_time_seconds=2.0,
        last_cast_time_seconds=None,
    )

    assert readiness.timing_ready is True
    assert readiness.expires_at_seconds is None


def test_maintenance_is_not_ready_while_effect_is_still_active() -> None:
    readiness = assess_rotation_maintenance_readiness(
        candidate=_candidate(),
        decision_time_seconds=10.0,
        last_cast_time_seconds=0.0,
        refresh_lead_seconds=1.0,
    )

    assert readiness.ready_at_seconds == 14.0
    assert readiness.expires_at_seconds == 15.0
    assert readiness.timing_ready is False


def test_maintenance_becomes_ready_when_refresh_window_opens() -> None:
    readiness = assess_rotation_maintenance_readiness(
        candidate=_candidate(),
        decision_time_seconds=14.0,
        last_cast_time_seconds=0.0,
        refresh_lead_seconds=1.0,
    )

    assert readiness.timing_ready is True


def test_refresh_lead_cannot_exceed_canonical_duration() -> None:
    with pytest.raises(ValueError, match="cannot exceed canonical duration"):
        assess_rotation_maintenance_readiness(
            candidate=_candidate(),
            decision_time_seconds=1.0,
            last_cast_time_seconds=0.0,
            refresh_lead_seconds=16.0,
        )


def test_readiness_bridges_into_action_eligibility_without_swallowing_other_legality() -> None:
    readiness = assess_rotation_maintenance_readiness(
        candidate=_candidate(),
        decision_time_seconds=14.0,
        last_cast_time_seconds=0.0,
        refresh_lead_seconds=1.0,
    )

    eligibility = eligibility_from_maintenance_readiness(
        readiness=readiness,
        resource_safe=False,
        encounter_allowed=True,
        reason="paired-cage reserve would be violated",
    )

    assert eligibility.timing_ready is True
    assert eligibility.resource_safe is False
    assert eligibility.encounter_allowed is True
    assert eligibility.legal is False
    assert "refresh window is open" in eligibility.reason
    assert "paired-cage reserve" in eligibility.reason
