from types import SimpleNamespace

from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationExtractor,
)


def _activation(event_index: int, timestamp: float):
    return (
        event_index,
        SimpleNamespace(timestamp=timestamp),
    )


def test_previous_activation_seconds_returns_nearest_prior_activation():
    activations = (
        _activation(10, 10000),
        _activation(20, 18000),
        _activation(30, 35000),
    )

    previous = RotationHealerEsoLogsObservationExtractor._previous_activation_seconds(
        activations,
        before_event_index=30,
        scale=0.001,
    )

    assert previous == 18.0


def test_previous_activation_seconds_is_none_for_first_activation():
    activations = (
        _activation(10, 10000),
        _activation(20, 18000),
    )

    previous = RotationHealerEsoLogsObservationExtractor._previous_activation_seconds(
        activations,
        before_event_index=10,
        scale=0.001,
    )

    assert previous is None


def test_previous_activation_gap_can_be_compared_to_canonical_duration():
    activations = (
        _activation(10, 10000),
        _activation(20, 18000),
    )
    previous = RotationHealerEsoLogsObservationExtractor._previous_activation_seconds(
        activations,
        before_event_index=20,
        scale=0.001,
    )

    activation_seconds = 18.0
    canonical_duration_seconds = 10.0
    expiry_tolerance_seconds = 0.02

    assert previous is not None
    assert (
        activation_seconds - previous
        < canonical_duration_seconds - expiry_tolerance_seconds
    )
