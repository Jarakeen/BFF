from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse, ExtremeRuntimeSnapshot
from services.rotation_runtime_bar_provenance_service import RotationRuntimeBarProvenanceService


def _attempt(time_seconds: float, sequence: int):
    return RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=time_seconds,
            trigger="overheal_self_or_ally",
            source="rotation provenance test",
            sequence=sequence,
        )
    )


def _plan():
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=10.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Front Heal", "front"),
            RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(5.0, 1, RotationActionKind.SKILL, "Back Heal", "back"),
        ),
    )


def test_unbarred_attempts_are_tagged_and_bar_swaps_are_projected():
    front = _attempt(1.0, 0)
    back = _attempt(5.0, 1)
    potion = ExtremeRuntimePotionUse(time_seconds=2.0, sequence=0)
    source = ExtremeRuntimeSnapshot(
        runtime_history=(back, potion, front),
        snapshot_time_seconds=8.0,
    )

    result = RotationRuntimeBarProvenanceService().bind(_plan(), source)

    assert result.resolved
    assert result.attempts_tagged == 2
    assert result.attempts_verified == 0
    assert result.transitions_projected == 1
    assert result.snapshot is not None
    assert result.snapshot.bar_transition_history_complete is True
    assert result.snapshot.bar_transitions == (
        ExtremeRuntimeBarTransition(5.0, 0, "front", "back"),
    )
    assert tuple(row.active_bar for row in result.snapshot.bar_effect_attempts) == (
        "front",
        "back",
    )
    assert result.snapshot.effect_attempts == (front, back)
    assert result.snapshot.unbarred_effect_attempts == ()
    assert potion in result.snapshot.runtime_history


def test_same_timestamp_sequence_respects_bar_swap_order():
    before_swap = _attempt(5.0, 0)
    after_swap = _attempt(5.0, 1)
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=10.0,
        actions=(
            RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(5.0, 1, RotationActionKind.SKILL, "Back Heal", "back"),
        ),
    )
    source = ExtremeRuntimeSnapshot(
        runtime_history=(before_swap, after_swap),
        snapshot_time_seconds=6.0,
    )

    result = RotationRuntimeBarProvenanceService().bind(plan, source)

    assert result.resolved
    assert result.snapshot is not None
    assert tuple(row.active_bar for row in result.snapshot.bar_effect_attempts) == (
        "back",
        "back",
    )
    assert result.snapshot.bar_transitions == (
        ExtremeRuntimeBarTransition(5.0, 0, "front", "back"),
    )


def test_existing_bar_tag_is_verified_against_plan_and_mismatch_fails_closed():
    tagged = ExtremeRuntimeBarEffectAttempt(_attempt(5.0, 1), active_bar="front")
    source = ExtremeRuntimeSnapshot(
        runtime_history=(tagged,),
        snapshot_time_seconds=6.0,
    )

    result = RotationRuntimeBarProvenanceService().bind(_plan(), source)

    assert not result.resolved
    assert result.snapshot is None
    assert any("disagrees with RotationPlan" in row for row in result.unresolved)


def test_existing_transition_history_is_verified_against_plan():
    bad_transition = ExtremeRuntimeBarTransition(4.0, 0, "front", "back")
    source = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, 0), bad_transition),
        snapshot_time_seconds=8.0,
        bar_transition_history_complete=True,
    )

    result = RotationRuntimeBarProvenanceService().bind(_plan(), source)

    assert not result.resolved
    assert result.snapshot is None
    assert result.unresolved == (
        "runtime bar-transition evidence disagrees with RotationPlan BAR_SWAP history",
    )


def test_illegal_plan_and_legacy_snapshot_fail_closed():
    illegal = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Wrong Bar", "back"),
        ),
    )
    source = ExtremeRuntimeSnapshot(
        runtime_history=(_attempt(1.0, 0),),
        snapshot_time_seconds=2.0,
    )
    illegal_result = RotationRuntimeBarProvenanceService().bind(illegal, source)
    legacy_result = RotationRuntimeBarProvenanceService().bind(
        _plan(),
        ExtremeRuntimeSnapshot(attempts=(_attempt(1.0, 0),), snapshot_time_seconds=2.0),
    )

    assert not illegal_result.resolved
    assert any("bar legality violation" in row for row in illegal_result.unresolved)
    assert not legacy_result.resolved
    assert any("requires authoritative runtime_history" in row for row in legacy_result.unresolved)
