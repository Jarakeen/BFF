import pytest

from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingResolution,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRuntimeEvidenceService,
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRefreshPolicy,
)


def _canonical(*, unresolved=()):
    return RotationHealerCanonicalPeriodicTimingResolution(
        source_name="Budding Seeds",
        coefficient_number=2,
        skill_rank_id=123,
        ability_id=456,
        component_fragment="While the field grows, you and allies are healed for $2 Health every 1 second.",
        timing=SkillComponentRuntimeTiming(
            interval_seconds=1.0,
            bound_kind=RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW,
            evidence="every 1 second",
        ),
        duration_seconds=6.0,
        evidence=("canonical cadence", "canonical duration"),
        unresolved=unresolved,
    )


def _observation(**overrides):
    values = {
        "source_name": "Budding Seeds",
        "coefficient_number": 2,
        "first_tick_offset_seconds": 1.0,
        "tick_on_expiry_boundary": True,
        "refresh_policy": None,
        "provenance": ("reviewed combat-log sample",),
        "game_version": "U50",
    }
    values.update(overrides)
    return RotationHealerReviewedRuntimeObservation(**values)


def test_single_application_fails_closed_without_reviewed_runtime_observation():
    result = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=_canonical(),
    )

    assert not result.ready
    assert result.runtime_evidence is None
    assert any("first-tick offset" in item for item in result.unresolved)
    assert any("tick-at-expiry" in item for item in result.unresolved)
    assert not any("refresh/recast" in item for item in result.unresolved)


def test_single_application_becomes_runtime_ready_when_missing_facts_are_reviewed():
    result = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=_canonical(),
        observation=_observation(),
    )

    assert result.ready
    assert result.runtime_evidence is not None
    assert result.runtime_evidence.duration_seconds == 6.0
    assert result.runtime_evidence.tick_interval_seconds == 1.0
    assert result.runtime_evidence.first_tick_offset_seconds == 1.0
    assert result.runtime_evidence.tick_on_expiry_boundary is True
    assert result.runtime_evidence.refresh_policy is None
    assert "reviewed runtime game version: U50" in result.evidence


def test_repeated_applications_require_refresh_policy_even_when_single_cast_facts_are_known():
    result = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=_canonical(),
        observation=_observation(),
        repeated_applications=True,
    )

    assert not result.ready
    assert result.runtime_evidence is None
    assert any("refresh/recast" in item for item in result.unresolved)


def test_repeated_applications_can_become_ready_from_reviewed_restart_evidence():
    result = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=_canonical(),
        observation=_observation(
            refresh_policy=RotationHealerPeriodicRefreshPolicy.RESTART,
        ),
        repeated_applications=True,
    )

    assert result.ready
    assert result.runtime_evidence is not None
    assert result.runtime_evidence.refresh_policy is RotationHealerPeriodicRefreshPolicy.RESTART


def test_observation_identity_must_match_the_canonical_component():
    result = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=_canonical(),
        observation=_observation(source_name="Illustrious Healing"),
    )

    assert not result.ready
    assert result.runtime_evidence is None
    assert any("identity does not match" in item for item in result.unresolved)


def test_reviewed_runtime_fact_requires_provenance():
    with pytest.raises(ValueError, match="require provenance"):
        RotationHealerReviewedRuntimeObservation(
            source_name="Budding Seeds",
            coefficient_number=2,
            first_tick_offset_seconds=1.0,
            tick_on_expiry_boundary=True,
        )


def test_canonical_unresolved_still_blocks_runtime_evidence_even_with_complete_observation():
    result = RotationHealerPeriodicRuntimeEvidenceService().resolve(
        canonical=_canonical(unresolved=("component-specific duration ambiguity",)),
        observation=_observation(),
    )

    assert not result.ready
    assert result.runtime_evidence is None
    assert "component-specific duration ambiguity" in result.unresolved
