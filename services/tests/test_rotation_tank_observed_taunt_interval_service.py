from services.rotation_tank_observed_taunt_interval_service import (
    ObservedTauntStateEvent,
    RotationTankObservedTauntIntervalService,
)


def _event(time_ms, event_type, *, instance=1, source_id=1):
    return ObservedTauntStateEvent(
        report_code="report",
        fight_id=34,
        actor_name="Iron Atronach",
        target_instance=instance,
        source_id=source_id,
        timestamp_ms=time_ms,
        event_type=event_type,
    )


def test_projector_preserves_exact_logged_duration():
    result = RotationTankObservedTauntIntervalService().project(
        (_event(1000.0, "applydebuff"), _event(16000.0, "removedebuff"))
    )
    assert len(result) == 1
    assert result[0].duration_ms == 15000.0


def test_projector_preserves_early_removal_instead_of_padding_to_taunt_duration():
    result = RotationTankObservedTauntIntervalService().project(
        (_event(1000.0, "applydebuff"), _event(5500.0, "removedebuff"))
    )
    assert result[0].duration_ms == 4500.0


def test_projector_leaves_unmatched_apply_open():
    result = RotationTankObservedTauntIntervalService().project(
        (_event(1000.0, "applydebuff"),)
    )
    assert len(result) == 1
    assert result[0].end_ms is None
    assert result[0].duration_ms is None
