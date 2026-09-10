import pytest

from services.rotation_healer_periodic_runtime_observation_service import (
    RotationHealerPeriodicObservedSample,
    RotationHealerPeriodicRuntimeObservationService,
)


def _sample(*, ticks=(11.0, 12.0, 13.0, 14.0, 15.0, 16.0), end=16.1):
    return RotationHealerPeriodicObservedSample(
        source_name="Budding Seeds",
        coefficient_number=2,
        activation_time_seconds=10.0,
        observed_tick_times_seconds=tuple(ticks),
        observation_end_seconds=end,
        provenance=("reviewed combat-log sample A",),
        game_version="U50",
    )


def test_derives_first_tick_and_expiry_boundary_from_complete_observation():
    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=_sample(),
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
    )

    assert result.observation is not None
    assert result.observation.first_tick_offset_seconds == 1.0
    assert result.observation.tick_on_expiry_boundary is True
    assert result.observation.refresh_policy is None
    assert result.unresolved == ()
    assert any("canonical 1s cadence" in item for item in result.evidence)


def test_observation_without_expiry_coverage_does_not_invent_boundary_rule():
    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=_sample(ticks=(11.0, 12.0, 13.0), end=13.2),
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
    )

    assert result.observation is None
    assert any("does not extend through canonical expiry" in item for item in result.unresolved)


def test_complete_observation_can_prove_no_tick_on_expiry_boundary():
    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=_sample(ticks=(11.0, 12.0, 13.0, 14.0, 15.0), end=16.1),
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
    )

    assert result.observation is not None
    assert result.observation.tick_on_expiry_boundary is False


def test_spacing_conflict_is_reported_without_silently_changing_canonical_cadence():
    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=_sample(ticks=(11.0, 12.25, 13.25, 14.25, 15.25, 16.0)),
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
    )

    assert result.observation is not None
    assert any("conflicts with canonical cadence" in item for item in result.unresolved)


def test_cadence_jitter_tolerance_does_not_loosen_expiry_boundary_truth():
    sample = _sample(
        ticks=(10.04, 11.08, 12.03, 13.07, 14.01, 15.06, 16.018),
        end=16.02,
    )

    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=sample,
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
    )

    assert result.observation is not None
    assert result.observation.tick_on_expiry_boundary is False
    assert not any("conflicts with canonical cadence" in item for item in result.unresolved)
    assert any("canonical 1s cadence" in item for item in result.evidence)


def test_cadence_tolerance_can_be_tightened_without_changing_expiry_tolerance():
    sample = _sample(
        ticks=(10.04, 11.08, 12.03, 13.07, 14.01, 15.06, 16.018),
        end=16.02,
    )

    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=sample,
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
        cadence_tolerance_seconds=0.01,
    )

    assert result.observation is not None
    assert result.observation.tick_on_expiry_boundary is False
    assert any("conflicts with canonical cadence" in item for item in result.unresolved)


def test_rejects_invalid_cadence_tolerance():
    with pytest.raises(ValueError, match="cadence_tolerance_seconds"):
        RotationHealerPeriodicRuntimeObservationService().resolve(
            sample=_sample(),
            canonical_duration_seconds=6.0,
            canonical_cadence_seconds=1.0,
            cadence_tolerance_seconds=-0.01,
        )


def test_sample_requires_provenance():
    with pytest.raises(ValueError, match="requires provenance"):
        RotationHealerPeriodicObservedSample(
            source_name="Illustrious Healing",
            coefficient_number=1,
            activation_time_seconds=5.0,
            observed_tick_times_seconds=(6.0,),
            observation_end_seconds=20.0,
            provenance=(),
        )


def test_empty_tick_sample_fails_closed():
    result = RotationHealerPeriodicRuntimeObservationService().resolve(
        sample=_sample(ticks=(), end=16.1),
        canonical_duration_seconds=6.0,
        canonical_cadence_seconds=1.0,
    )

    assert result.observation is None
    assert any("no periodic heal event was observed" in item for item in result.unresolved)
