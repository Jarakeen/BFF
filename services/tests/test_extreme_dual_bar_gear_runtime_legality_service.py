from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from services.extreme_dual_bar_gear_runtime_legality_service import (
    ExtremeDualBarGearRuntimeLegalityService,
    ExtremeGearRuntimeBarAttempt,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationScope,
)


class _Resolver:
    def __init__(self, effects_by_set):
        self.effects_by_set = effects_by_set

    def resolve(self, set_id, equipped_piece_count):
        return [
            effect
            for required, effect in self.effects_by_set.get(int(set_id), ())
            if int(required) <= int(equipped_piece_count)
        ]


def _proc(source: str, *, name="major_courage", trigger="overheal_self_or_ally"):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=source,
        duration=5.0,
        cooldown=10.0,
        trigger=trigger,
        target_type=SupportTargetType.SELF,
        stacking=StackingBehavior.UNIQUE,
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
    return ExtremeGearRuntimeBarAttempt(
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


def test_front_only_five_piece_can_trigger_on_front_and_persist_after_swap():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            _evidence(
                set_id=10,
                name="Front Set",
                front_count=5,
                back_count=3,
                front_breakpoints=(2, 3, 4, 5),
                back_breakpoints=(2, 3),
            ),
        )
    )
    service = ExtremeDualBarGearRuntimeLegalityService(
        resolver=_Resolver({10: ((5, _proc("Front Set (5)")),)}),
    )

    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=3.0,
    )

    assert result.active_buffs == ("Major Courage",)
    assert result.attempts_rejected_inactive_breakpoint == 0
    assert result.unresolved == ()


def test_front_only_five_piece_cannot_proc_from_back_bar_trigger():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            _evidence(
                set_id=10,
                name="Front Set",
                front_count=5,
                back_count=3,
                front_breakpoints=(2, 3, 4, 5),
                back_breakpoints=(2, 3),
            ),
        )
    )
    service = ExtremeDualBarGearRuntimeLegalityService(
        resolver=_Resolver({10: ((5, _proc("Front Set (5)")),)}),
    )

    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="back"),),
        snapshot_time_seconds=2.0,
    )

    assert result.active_buffs == ()
    assert result.attempts_rejected_inactive_breakpoint == 1
    assert result.unresolved == ()


def test_back_bar_weapon_only_package_can_proc_only_on_back_bar():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            _evidence(
                set_id=20,
                name="Arena Weapon",
                front_count=0,
                back_count=2,
                front_breakpoints=(),
                back_breakpoints=(2,),
                weapon_only=True,
            ),
        )
    )
    service = ExtremeDualBarGearRuntimeLegalityService(
        resolver=_Resolver({20: ((2, _proc("Arena Weapon (2)")),)}),
    )

    result = service.resolve_history(
        activation,
        attempts=(
            _attempt(1.0, bar="front", sequence=0),
            _attempt(2.0, bar="back", sequence=1),
        ),
        snapshot_time_seconds=3.0,
    )

    assert result.active_buffs == ("Major Courage",)
    assert result.attempts_reviewed == 2
    assert result.attempts_rejected_inactive_breakpoint == 1


def test_missing_breakpoint_provenance_fails_closed():
    activation = ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            _evidence(
                set_id=30,
                name="Unknown Breakpoint",
                front_count=5,
                back_count=5,
                front_breakpoints=(5,),
                back_breakpoints=(5,),
            ),
        )
    )
    service = ExtremeDualBarGearRuntimeLegalityService(
        resolver=_Resolver({30: ((5, _proc("Unknown Breakpoint")),)}),
    )

    result = service.resolve_history(
        activation,
        attempts=(_attempt(1.0, bar="front"),),
        snapshot_time_seconds=2.0,
    )

    assert result.active_buffs == ()
    assert any("no canonical set-breakpoint provenance" in row for row in result.unresolved)


def test_invalid_runtime_bar_fails_closed_immediately():
    try:
        _attempt(1.0, bar="middle")
    except ValueError as exc:
        assert "unsupported Extreme gear runtime bar" in str(exc)
    else:
        raise AssertionError("expected invalid runtime bar to fail closed")
