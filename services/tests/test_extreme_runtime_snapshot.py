from __future__ import annotations

import pytest

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from services.extreme_runtime_snapshot import (
    ExtremeRuntimePotionUse,
    ExtremeRuntimeSnapshot,
)


def _attempt(*, time_seconds: float, sequence: int = 0) -> RuntimeEffectEventAttempt:
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=time_seconds,
            trigger="critical_heal",
            source="unified runtime snapshot test",
            sequence=sequence,
        )
    )


def test_unified_runtime_history_orders_effects_and_potion_uses_together():
    late_attempt = _attempt(time_seconds=8.0, sequence=2)
    early_attempt = _attempt(time_seconds=2.0, sequence=3)
    potion_use = ExtremeRuntimePotionUse(time_seconds=2.0, sequence=1)

    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(late_attempt, early_attempt, potion_use),
        snapshot_time_seconds=10.0,
    )

    assert snapshot.ordered_runtime_history == (
        potion_use,
        early_attempt,
        late_attempt,
    )
    assert snapshot.effect_attempts == (early_attempt, late_attempt)
    assert snapshot.effective_potion_elapsed_seconds == pytest.approx(8.0)
    assert snapshot.has_runtime_history_at_snapshot


def test_unified_runtime_history_uses_latest_potion_activation_before_snapshot():
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(
            ExtremeRuntimePotionUse(time_seconds=1.0),
            ExtremeRuntimePotionUse(time_seconds=7.5),
        ),
        snapshot_time_seconds=10.0,
    )

    assert snapshot.effective_potion_elapsed_seconds == pytest.approx(2.5)


def test_unified_runtime_history_ignores_future_potion_activation():
    future_potion = ExtremeRuntimePotionUse(time_seconds=12.0)
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(future_potion,),
        snapshot_time_seconds=10.0,
    )

    assert snapshot.effective_potion_elapsed_seconds is None
    assert not snapshot.has_runtime_history_at_snapshot


def test_unified_runtime_history_rejects_mixed_legacy_inputs():
    with pytest.raises(
        ValueError,
        match="runtime_history cannot be combined with legacy attempts or potion_elapsed_seconds",
    ):
        ExtremeRuntimeSnapshot(
            runtime_history=(ExtremeRuntimePotionUse(time_seconds=1.0),),
            snapshot_time_seconds=5.0,
            attempts=(_attempt(time_seconds=2.0),),
        )


def test_legacy_runtime_inputs_remain_supported_during_migration():
    attempt = _attempt(time_seconds=1.0)
    snapshot = ExtremeRuntimeSnapshot(
        attempts=(attempt,),
        snapshot_time_seconds=5.0,
        potion_elapsed_seconds=3.0,
    )

    assert snapshot.effect_attempts == (attempt,)
    assert snapshot.effective_potion_elapsed_seconds == pytest.approx(3.0)
    assert snapshot.has_runtime_history_at_snapshot


def test_runtime_potion_use_rejects_invalid_time_and_sequence():
    with pytest.raises(ValueError, match="runtime potion-use time"):
        ExtremeRuntimePotionUse(time_seconds=-1.0)
    with pytest.raises(ValueError, match="runtime potion-use sequence"):
        ExtremeRuntimePotionUse(time_seconds=1.0, sequence=-1)
