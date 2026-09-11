from types import SimpleNamespace

import pytest

from services.rotation_healer_action_healing_service import RotationHealerChannelHealSeed
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelMagnitudePolicy,
    RotationHealerChannelMagnitudeResolution,
    RotationHealerChannelRuntimeEvidence,
    RotationHealerChannelRuntimeService,
)


def _seed(*, time_seconds=4.0, sequence=2, modeled_heal=300.0):
    return RotationHealerChannelHealSeed(
        time_seconds=time_seconds,
        sequence=sequence,
        source_name="Healing Channel",
        coefficient_number=1,
        modeled_heal=modeled_heal,
    )


def _evidence(*, policy=RotationHealerChannelMagnitudePolicy.SNAPSHOT_AT_CAST):
    return RotationHealerChannelRuntimeEvidence(
        source_name="Healing Channel",
        coefficient_number=1,
        channel_duration_seconds=3.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_channel_end_boundary=True,
        magnitude_policy=policy,
        provenance=("reviewed channel fixture",),
    )


def test_channel_runtime_schedules_reviewed_ticks_inside_channel_window():
    result = RotationHealerChannelRuntimeService().project(
        seeds=(_seed(),),
        evidence=(_evidence(),),
        horizon_seconds=20.0,
    )

    assert result.unresolved == ()
    assert [event.time_seconds for event in result.events] == [5.0, 6.0, 7.0]
    assert [event.modeled_heal for event in result.events] == [300.0, 300.0, 300.0]


def test_channel_runtime_can_exclude_tick_on_channel_end_boundary():
    evidence = RotationHealerChannelRuntimeEvidence(
        source_name="Healing Channel",
        coefficient_number=1,
        channel_duration_seconds=3.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_channel_end_boundary=False,
        magnitude_policy=RotationHealerChannelMagnitudePolicy.SNAPSHOT_AT_CAST,
        provenance=("reviewed channel fixture",),
    )

    result = RotationHealerChannelRuntimeService().project(
        seeds=(_seed(),),
        evidence=(evidence,),
        horizon_seconds=20.0,
    )

    assert [event.time_seconds for event in result.events] == [5.0, 6.0]


def test_recalculate_each_tick_uses_runtime_magnitude_resolver():
    calls = []

    def resolver(seed, time_seconds, sequence):
        calls.append((seed.source_name, time_seconds, sequence))
        return RotationHealerChannelMagnitudeResolution(
            modeled_heal=100.0 + time_seconds,
        )

    result = RotationHealerChannelRuntimeService().project(
        seeds=(_seed(),),
        evidence=(
            _evidence(
                policy=RotationHealerChannelMagnitudePolicy.RECALCULATE_EACH_TICK,
            ),
        ),
        horizon_seconds=20.0,
        runtime_magnitude_resolver=resolver,
    )

    assert [event.modeled_heal for event in result.events] == [105.0, 106.0, 107.0]
    assert [call[1] for call in calls] == [5.0, 6.0, 7.0]
    assert result.unresolved == ()


def test_dynamic_channel_magnitude_requires_reviewed_policy():
    evidence = RotationHealerChannelRuntimeEvidence(
        source_name="Healing Channel",
        coefficient_number=1,
        channel_duration_seconds=3.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_channel_end_boundary=True,
        magnitude_policy=None,
        provenance=("reviewed channel fixture",),
    )

    result = RotationHealerChannelRuntimeService().project(
        seeds=(_seed(),),
        evidence=(evidence,),
        horizon_seconds=20.0,
        runtime_magnitude_resolver=lambda *args: SimpleNamespace(
            resolved=True,
            modeled_heal=999.0,
            unresolved=(),
        ),
    )

    assert result.events == ()
    assert result.unresolved == (
        "Healing Channel coefficient 1: channel healing magnitude snapshot/recalculation policy is not canonically verified",
    )


def test_missing_channel_runtime_evidence_fails_closed():
    result = RotationHealerChannelRuntimeService().project(
        seeds=(_seed(),),
        evidence=(),
        horizon_seconds=20.0,
    )

    assert result.events == ()
    assert result.unresolved == (
        "Healing Channel coefficient 1: channel healing runtime evidence unavailable",
    )


def test_channel_runtime_clips_ticks_at_plan_horizon():
    result = RotationHealerChannelRuntimeService().project(
        seeds=(_seed(time_seconds=4.0),),
        evidence=(_evidence(),),
        horizon_seconds=5.5,
    )

    assert [event.time_seconds for event in result.events] == [5.0]


def test_channel_runtime_rejects_first_tick_after_channel_duration():
    with pytest.raises(ValueError, match="first channel-heal tick"):
        RotationHealerChannelRuntimeEvidence(
            source_name="Healing Channel",
            coefficient_number=1,
            channel_duration_seconds=2.0,
            tick_interval_seconds=1.0,
            first_tick_offset_seconds=3.0,
            tick_on_channel_end_boundary=True,
            provenance=("reviewed channel fixture",),
        )
