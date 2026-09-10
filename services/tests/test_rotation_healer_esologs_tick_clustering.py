from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationExtractor,
)


def test_collapses_near_simultaneous_recipient_events_to_earliest_tick():
    collapsed = RotationHealerEsoLogsObservationExtractor._collapse_recipient_tick_times(
        (11.000, 11.007, 11.019, 12.000, 12.013, 13.001),
        merge_tolerance_seconds=0.05,
    )

    assert collapsed == (11.0, 12.0, 13.001)


def test_cluster_span_is_anchored_to_first_event_not_chained_indefinitely():
    collapsed = RotationHealerEsoLogsObservationExtractor._collapse_recipient_tick_times(
        (11.000, 11.040, 11.080),
        merge_tolerance_seconds=0.05,
    )

    assert collapsed == (11.0, 11.08)


def test_zero_tolerance_only_deduplicates_exact_timestamp():
    collapsed = RotationHealerEsoLogsObservationExtractor._collapse_recipient_tick_times(
        (11.000, 11.000, 11.001),
        merge_tolerance_seconds=0.0,
    )

    assert collapsed == (11.0, 11.001)


def test_negative_merge_tolerance_is_rejected():
    try:
        RotationHealerEsoLogsObservationExtractor._collapse_recipient_tick_times(
            (11.0,),
            merge_tolerance_seconds=-0.001,
        )
    except ValueError as exc:
        assert "merge_tolerance_seconds must be non-negative" in str(exc)
    else:
        raise AssertionError("negative merge tolerance should fail closed")
