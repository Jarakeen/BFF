from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.effect_source_persistence import EffectSourcePersistence
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from services.extreme_dual_bar_gear_runtime_legality_service import (
    ExtremeDualBarGearRuntimeLegalityService,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationScope,
)
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition


class _Resolver:
    def __init__(self, effects_by_set):
        self.effects_by_set = effects_by_set

    def resolve(self, set_id, equipped_piece_count):
        return [
            effect
            for required, effect in self.effects_by_set.get(int(set_id), ())
            if int(required) <= int(equipped_piece_count)
        ]


def _proc(
    source: str,
    *,
    name="major_courage",
    trigger="overheal_self_or_ally",
    persistence=EffectSourcePersistence.PERSISTS_AFTER_ACTIVATION,
):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=source,
        duration=5.0,
        cooldown=10.0,
        trigger=trigger,
        target_type=SupportTargetType.SELF,
        stacking=StackingBehavior.UNIQUE,
        source_persistence=persistence,
    )


def _evidence(
    *,
    set_id: int,
    name: str,
    front_count: int,
    back_count: int,
    front_breakpoints=(),
    back_breakpoints=(),
    weapon_only=False,
):
    front = tuple(front_breakpoints)
    back = tuple(back_breakpoints)
    if front and back:
        scope = ExtremeDualBarSetActivationScope.BOTH
    elif front:
        scope = ExtremeDualBarSetActivationScope.FRONT_ONLY
    elif back:
        scope = ExtremeDualBarSetActivationScope.BACK_ONLY
    else:
        scope = ExtremeDualBarSetActivationScope.INACTIVE
    return ExtremeDualBarSetActivationEvidence(
        set_id=set_id,
        set_name=name,
        category="Arena" if weapon_only else "Trial",
        front_count=front_count,
        back_count=back_count,
        front_active_breakpoints=front,
        back_active_breakpoints=back,
        activation_scope=scope,
        weapon_only_two_piece=weapon_only,
    )


def _attempt(time_seconds: float, *, bar: str, trigger="overheal_self_or_ally", sequence=0):
    return ExtremeRuntimeBarEffectAttempt(
        RuntimeEffectEventAttempt(
            RuntimeEvent(
                time_seconds=time_seconds,
                trigger=trigger,
                source=f"{bar} trigger",
                sequence=sequence,
            )
        ),
        active_bar=bar,
    )


def _transition(time_seconds: float, *, sequence: int, from_bar: str, to_bar: str):
    return ExtremeRuntimeBarTransition(time_seconds, sequence, from_bar, to_bar)


def test_front_only_five_piece_can_trigger_on_front_and_persist_after_swap():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(_evidence(set_id=10, name="Front Set", front_count=5, back_count=3, front_breakpoints=(2, 3, 4, 5), back_breakpoints=(2, 3)),)
    )
    service = ExtremeDualBarGearRuntimeLegalityService(
        resolver=_Resolver({10: ((5, _proc("Front Set (5)")),)}),
    )
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=3.0,
        snapshot_active_bar="back",
    )
    assert result.active_buffs == ("Major Courage",)
    assert result.attempts_rejected_inactive_breakpoint == 0
    assert result.unresolved == ()


def test_front_only_five_piece_cannot_proc_from_back_bar_trigger():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(_evidence(set_id=10, name="Front Set", front_count=5, back_count=3, front_breakpoints=(2, 3, 4, 5), back_breakpoints=(2, 3)),)
    )
    service = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver({10: ((5, _proc("Front Set (5)")),)}))
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="back"),),
        snapshot_time_seconds=2.0,
        snapshot_active_bar="back",
    )
    assert result.active_buffs == ()
    assert result.attempts_rejected_inactive_breakpoint == 1
    assert result.unresolved == ()


def test_back_bar_weapon_only_package_can_proc_only_on_back_bar():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(_evidence(set_id=20, name="Arena Weapon", front_count=0, back_count=2, back_breakpoints=(2,), weapon_only=True),)
    )
    service = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver({20: ((2, _proc("Arena Weapon (2)")),)}))
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front", sequence=0), _attempt(2.0, bar="back", sequence=1)),
        snapshot_time_seconds=3.0,
        snapshot_active_bar="front",
    )
    assert result.active_buffs == ("Major Courage",)
    assert result.attempts_reviewed == 2
    assert result.attempts_rejected_inactive_breakpoint == 1


def test_missing_breakpoint_provenance_fails_closed():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(_evidence(set_id=30, name="Unknown Breakpoint", front_count=5, back_count=5, front_breakpoints=(5,), back_breakpoints=(5,)),)
    )
    service = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver({30: ((5, _proc("Unknown Breakpoint")),)}))
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=2.0,
        snapshot_active_bar="front",
    )
    assert result.active_buffs == ()
    assert any("no canonical set-breakpoint provenance" in row for row in result.unresolved)


def test_unclassified_proc_persistence_fails_closed():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(_evidence(set_id=40, name="Unknown Persistence", front_count=5, back_count=3, front_breakpoints=(5,)),)
    )
    service = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver({40: ((5, _proc("Unknown Persistence (5)", persistence=None)),)}))
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=2.0,
        snapshot_active_bar="back",
    )
    assert result.active_buffs == ()
    assert any("persistence after source deactivation is unclassified" in row for row in result.unresolved)


def test_source_active_at_snapshot_effect_drops_when_breakpoint_is_off_bar():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(_evidence(set_id=50, name="Source Bound", front_count=5, back_count=3, front_breakpoints=(5,)),)
    )
    effect = _proc("Source Bound (5)", persistence=EffectSourcePersistence.REQUIRES_SOURCE_ACTIVE_AT_SNAPSHOT)
    service = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver({50: ((5, effect),)}))
    off_bar = service.resolve_history(activation, attempts=(_attempt(1.0, bar="front"),), snapshot_time_seconds=2.0, snapshot_active_bar="back")
    on_bar = service.resolve_history(activation, attempts=(_attempt(1.0, bar="front"),), snapshot_time_seconds=2.0, snapshot_active_bar="front")
    assert off_bar.active_buffs == ()
    assert off_bar.unresolved == ()
    assert on_bar.active_buffs == ("Major Courage",)


def _strict_service_and_activation(*, both_bars: bool = False):
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            _evidence(
                set_id=60,
                name="Continuous Source",
                front_count=5,
                back_count=5 if both_bars else 3,
                front_breakpoints=(5,),
                back_breakpoints=(5,) if both_bars else (),
            ),
        )
    )
    effect = _proc("Continuous Source (5)", persistence=EffectSourcePersistence.ENDS_WHEN_SOURCE_INACTIVE)
    service = ExtremeDualBarGearRuntimeLegalityService(resolver=_Resolver({60: ((5, effect),)}))
    return service, activation


def test_ends_when_source_inactive_fails_closed_without_complete_transition_history():
    service, activation = _strict_service_and_activation()
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=2.0,
        snapshot_active_bar="front",
    )
    assert result.active_buffs == ()
    assert any("complete bar-transition history is required" in row for row in result.unresolved)


def test_ends_when_source_inactive_survives_when_complete_history_has_no_source_loss():
    service, activation = _strict_service_and_activation()
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=3.0,
        snapshot_active_bar="front",
        bar_transitions=(),
        bar_transition_history_complete=True,
    )
    assert result.active_buffs == ("Major Courage",)
    assert result.unresolved == ()


def test_ends_when_source_inactive_terminates_at_first_swap_off_source():
    service, activation = _strict_service_and_activation()
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front", sequence=0),),
        snapshot_time_seconds=3.0,
        snapshot_active_bar="back",
        bar_transitions=(_transition(2.0, sequence=0, from_bar="front", to_bar="back"),),
        bar_transition_history_complete=True,
    )
    assert result.active_buffs == ()
    assert result.unresolved == ()


def test_ends_when_source_inactive_does_not_resurrect_after_returning_to_source_bar():
    service, activation = _strict_service_and_activation()
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front", sequence=0),),
        snapshot_time_seconds=4.0,
        snapshot_active_bar="front",
        bar_transitions=(
            _transition(2.0, sequence=0, from_bar="front", to_bar="back"),
            _transition(3.0, sequence=0, from_bar="back", to_bar="front"),
        ),
        bar_transition_history_complete=True,
    )
    assert result.active_buffs == ()
    assert result.unresolved == ()


def test_ends_when_source_inactive_needs_no_transition_history_when_breakpoint_exists_on_both_bars():
    service, activation = _strict_service_and_activation(both_bars=True)
    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=3.0,
        snapshot_active_bar="back",
    )
    assert result.active_buffs == ("Major Courage",)
    assert result.unresolved == ()


def test_invalid_runtime_bar_fails_closed_immediately():
    try:
        _attempt(1.0, bar="middle")
    except ValueError as exc:
        assert "unsupported Extreme runtime effect bar" in str(exc)
    else:
        raise AssertionError("expected invalid runtime bar to fail closed")
