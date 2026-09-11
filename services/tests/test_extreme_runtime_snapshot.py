from __future__ import annotations

import pytest

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
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


def _bar_attempt(
    *,
    time_seconds: float,
    active_bar: str,
    sequence: int = 0,
) -> ExtremeRuntimeBarEffectAttempt:
    return ExtremeRuntimeBarEffectAttempt(
        attempt=_attempt(time_seconds=time_seconds, sequence=sequence),
        active_bar=active_bar,
    )


def _external_buff(*, time_seconds: float = 4.0, sequence: int = 0):
    return ExternalGroupBuffApplication(
        source_actor_id="healer_2",
        recipient_actor_id="healer_1",
        buff_name="Major Courage",
        target_type=SupportTargetType.SELF_OR_ALLY,
        applied_at_seconds=time_seconds,
        duration_seconds=8.0,
        source_evidence="observed external support application",
        sequence=sequence,
    )


def test_unified_runtime_history_orders_effects_potions_and_external_buffs_together():
    late_attempt = _attempt(time_seconds=8.0, sequence=2)
    early_attempt = _attempt(time_seconds=2.0, sequence=3)
    potion_use = ExtremeRuntimePotionUse(time_seconds=2.0, sequence=1)
    external_buff = _external_buff(time_seconds=4.0, sequence=1)

    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(late_attempt, external_buff, early_attempt, potion_use),
        snapshot_time_seconds=10.0,
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2", "healer_1"),
    )

    assert snapshot.ordered_runtime_history == (
        potion_use,
        early_attempt,
        external_buff,
        late_attempt,
    )
    assert snapshot.effect_attempts == (early_attempt, late_attempt)
    assert snapshot.external_group_buff_applications == (external_buff,)
    assert snapshot.effective_potion_elapsed_seconds == pytest.approx(8.0)
    assert snapshot.recipient_actor_id == "healer_1"
    assert snapshot.group_member_ids == ("healer_1", "healer_2")
    assert snapshot.has_runtime_history_at_snapshot


def test_bar_annotated_effect_attempt_preserves_provenance_and_compatibility_view():
    front = _bar_attempt(time_seconds=2.0, active_bar="front", sequence=2)
    unbarred = _attempt(time_seconds=3.0, sequence=0)
    back = _bar_attempt(time_seconds=4.0, active_bar="back", sequence=1)

    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(back, unbarred, front),
        snapshot_time_seconds=5.0,
    )

    assert snapshot.ordered_runtime_history == (front, unbarred, back)
    assert snapshot.bar_effect_attempts == (front, back)
    assert snapshot.unbarred_effect_attempts == (unbarred,)
    assert snapshot.effect_attempts == (front.attempt, unbarred, back.attempt)
    assert snapshot.attempts == snapshot.effect_attempts


def test_snapshot_at_preserves_bar_provenance_and_sequence_boundary():
    front = _bar_attempt(time_seconds=5.0, active_bar="front", sequence=0)
    back_before = _bar_attempt(time_seconds=10.0, active_bar="back", sequence=1)
    back_after = _bar_attempt(time_seconds=10.0, active_bar="back", sequence=3)
    source = ExtremeRuntimeSnapshot(
        runtime_history=(back_after, front, back_before),
        snapshot_time_seconds=20.0,
    )

    sliced = source.snapshot_at(10.0, sequence=2)

    assert sliced.runtime_history == (front, back_before)
    assert sliced.bar_effect_attempts == (front, back_before)
    assert sliced.effect_attempts == (front.attempt, back_before.attempt)


def test_invalid_bar_provenance_fails_closed():
    with pytest.raises(ValueError, match="unsupported Extreme runtime effect bar"):
        _bar_attempt(time_seconds=1.0, active_bar="middle")


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
    assert snapshot.bar_effect_attempts == ()
    assert snapshot.unbarred_effect_attempts == (attempt,)
    assert snapshot.external_group_buff_applications == ()
    assert snapshot.effective_potion_elapsed_seconds == pytest.approx(3.0)
    assert snapshot.has_runtime_history_at_snapshot


def test_legacy_positional_constructor_order_remains_compatible():
    attempt = _attempt(time_seconds=1.0)
    snapshot = ExtremeRuntimeSnapshot((attempt,), 5.0, 3.0)

    assert snapshot.attempts == (attempt,)
    assert snapshot.snapshot_time_seconds == pytest.approx(5.0)
    assert snapshot.potion_elapsed_seconds == pytest.approx(3.0)
    assert snapshot.runtime_history == ()
    assert snapshot.effect_attempts == (attempt,)
    assert snapshot.effective_potion_elapsed_seconds == pytest.approx(3.0)


def test_runtime_snapshot_at_respects_same_timestamp_sequence_boundary():
    early = ExtremeRuntimePotionUse(time_seconds=5.0, sequence=0)
    same_before = ExtremeRuntimePotionUse(time_seconds=10.0, sequence=0)
    same_after = ExtremeRuntimePotionUse(time_seconds=10.0, sequence=2)
    source = ExtremeRuntimeSnapshot(
        runtime_history=(same_after, early, same_before),
        snapshot_time_seconds=20.0,
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
    )

    sliced = source.snapshot_at(10.0, sequence=1)

    assert sliced.runtime_history == (early, same_before)
    assert sliced.snapshot_time_seconds == pytest.approx(10.0)
    assert sliced.effective_potion_elapsed_seconds == pytest.approx(0.0)
    assert sliced.recipient_actor_id == "healer_1"
    assert sliced.group_member_ids == ("healer_1", "healer_2")


def test_runtime_snapshot_at_refuses_to_time_shift_legacy_evidence():
    snapshot = ExtremeRuntimeSnapshot(
        snapshot_time_seconds=10.0,
        potion_elapsed_seconds=4.0,
    )

    assert snapshot.snapshot_at(10.0) is snapshot
    with pytest.raises(ValueError, match="legacy runtime snapshot evidence"):
        snapshot.snapshot_at(11.0)


def test_runtime_potion_use_rejects_invalid_time_and_sequence():
    with pytest.raises(ValueError, match="runtime potion-use time"):
        ExtremeRuntimePotionUse(time_seconds=-1.0)
    with pytest.raises(ValueError, match="runtime potion-use sequence"):
        ExtremeRuntimePotionUse(time_seconds=1.0, sequence=-1)
