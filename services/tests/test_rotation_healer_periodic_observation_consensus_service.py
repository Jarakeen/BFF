from types import SimpleNamespace

from services.rotation_healer_periodic_observation_consensus_service import (
    RotationHealerPeriodicObservationConsensusService,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_healer_periodic_runtime_observation_service import (
    RotationHealerPeriodicObservedResolution,
    RotationHealerPeriodicObservedSample,
)


def _entry(
    first_tick_offset: float,
    *,
    expiry: bool = False,
    unresolved: tuple[str, ...] = (),
    source_name: str = "Echoing Vigor",
    coefficient_number: int = 1,
    game_version: str = "U50",
):
    sample = RotationHealerPeriodicObservedSample(
        source_name=source_name,
        coefficient_number=coefficient_number,
        activation_time_seconds=10.0,
        observed_tick_times_seconds=(10.0 + first_tick_offset,),
        observation_end_seconds=30.0,
        provenance=(f"sample first={first_tick_offset:g}",),
        game_version=game_version,
    )
    observation = RotationHealerReviewedRuntimeObservation(
        source_name=source_name,
        coefficient_number=coefficient_number,
        first_tick_offset_seconds=first_tick_offset,
        tick_on_expiry_boundary=expiry,
        refresh_policy=None,
        provenance=(f"reviewed first={first_tick_offset:g}",),
        game_version=game_version,
    )
    observed = RotationHealerPeriodicObservedResolution(
        observation=observation,
        evidence=observation.provenance,
        unresolved=unresolved,
    )
    return SimpleNamespace(sample=sample, observed=observed)


def test_consensus_uses_median_and_preserves_observed_range_and_provenance():
    result = RotationHealerPeriodicObservationConsensusService().resolve(
        (_entry(0.021), _entry(0.023), _entry(0.021))
    )

    assert result.ready
    assert result.sample_count == 3
    assert result.first_tick_offset_range_seconds == (0.021, 0.023)
    assert result.observation is not None
    assert result.observation.first_tick_offset_seconds == 0.021
    assert result.observation.tick_on_expiry_boundary is False
    assert result.observation.refresh_policy is None
    assert any("consensus from 3" in item for item in result.evidence)
    assert any("median 0.021s" in item for item in result.evidence)
    assert any("reviewed first=0.023" in item for item in result.observation.provenance)


def test_consensus_fails_closed_when_expiry_observations_disagree():
    result = RotationHealerPeriodicObservationConsensusService().resolve(
        (_entry(0.04, expiry=False), _entry(0.05, expiry=True))
    )

    assert not result.ready
    assert result.observation is None
    assert any("expiry-boundary observations disagree" in item for item in result.unresolved)


def test_consensus_fails_closed_when_first_tick_spread_is_too_wide():
    result = RotationHealerPeriodicObservationConsensusService().resolve(
        (_entry(0.02), _entry(0.25))
    )

    assert not result.ready
    assert result.observation is None
    assert result.first_tick_offset_range_seconds == (0.02, 0.25)
    assert any("first-tick offsets disagree" in item for item in result.unresolved)


def test_consensus_rejects_any_reviewed_entry_with_runtime_conflict():
    result = RotationHealerPeriodicObservationConsensusService().resolve(
        (
            _entry(0.02),
            _entry(
                0.03,
                unresolved=("observed tick spacing conflicts with canonical cadence",),
            ),
        )
    )

    assert not result.ready
    assert result.observation is None
    assert any("sample 2" in item and "conflicts" in item for item in result.unresolved)


def test_consensus_rejects_mixed_component_identity_or_version():
    result = RotationHealerPeriodicObservationConsensusService().resolve(
        (_entry(0.02), _entry(0.03, game_version="U49"))
    )

    assert not result.ready
    assert result.observation is None
    assert any("identity/version" in item for item in result.unresolved)
