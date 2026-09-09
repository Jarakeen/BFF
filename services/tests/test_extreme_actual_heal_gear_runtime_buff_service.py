from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_eligibility import RuntimeEffectState
from minmax.runtime_event import RuntimeEvent
from minmax.support_target_type import SupportTargetType
from models.build_model import GearSlot, PlayerBuild
from services.extreme_actual_heal_gear_runtime_buff_service import (
    ExtremeActualHealGearRuntimeBuffService,
)


class _Repository:
    @staticmethod
    def get_set(name):
        return SimpleNamespace(id={"Self Proc Set": 1, "Ambiguous Proc Set": 2}.get(name, 0), name=name) if name in {"Self Proc Set", "Ambiguous Proc Set"} else None


class _Resolver:
    @staticmethod
    def resolve(set_id, piece_count):
        if piece_count < 5:
            return []
        target = SupportTargetType.SELF if set_id == 1 else SupportTargetType.ALLY
        return [
            EffectVariant(
                name="major_courage",
                layer=EffectLayer.PROC,
                source="fixture set",
                duration=5.0,
                cooldown=10.0,
                trigger="overheal_self_or_ally",
                target_type=target,
            )
        ]


def _five_piece(set_name):
    build = PlayerBuild(BuildName="Gear Proc")
    for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist"):
        build.Armor[slot]["Set"] = set_name
    return build


def test_self_target_gear_proc_reaches_named_buff_only_inside_live_window():
    service = ExtremeActualHealGearRuntimeBuffService(
        "unused.db", repository=_Repository(), resolver=_Resolver()
    )
    event = RuntimeEvent(
        time_seconds=10.0, trigger="overheal_self_or_ally", source="test"
    )
    result = service.resolve(
        _five_piece("Self Proc Set"),
        active_bar="front",
        event=event,
        snapshot_time_seconds=14.999,
    )
    assert result.active_buffs == ("Major Courage",)
    assert result.unresolved == ()

    expired = service.resolve(
        _five_piece("Self Proc Set"),
        active_bar="front",
        event=event,
        snapshot_time_seconds=15.0,
    )
    assert expired.active_buffs == ()


def test_nonself_gear_proc_is_not_promoted_to_wearer_buff():
    service = ExtremeActualHealGearRuntimeBuffService(
        "unused.db", repository=_Repository(), resolver=_Resolver()
    )
    event = RuntimeEvent(
        time_seconds=0.0, trigger="overheal_self_or_ally", source="test"
    )
    result = service.resolve(
        _five_piece("Ambiguous Proc Set"),
        active_bar="front",
        event=event,
        snapshot_time_seconds=1.0,
    )
    assert result.active_buffs == ()
    assert any("does not canonically prove wearer self-application" in item for item in result.unresolved)


def test_gear_proc_respects_cooldown_state():
    service = ExtremeActualHealGearRuntimeBuffService(
        "unused.db", repository=_Repository(), resolver=_Resolver()
    )
    event = RuntimeEvent(
        time_seconds=10.0, trigger="overheal_self_or_ally", source="test"
    )
    result = service.resolve(
        _five_piece("Self Proc Set"),
        active_bar="front",
        event=event,
        snapshot_time_seconds=11.0,
        state=RuntimeEffectState(last_activation_time_seconds=5.0),
    )
    assert result.active_buffs == ()


def test_gear_proc_uses_canonical_two_slot_weapon_counting():
    build = PlayerBuild(
        BuildName="Weapon Count",
        FrontBarWeapon=GearSlot(
            Set="Self Proc Set", WeaponType="Restoration Staff"
        ),
    )
    for slot in ("Head", "Shoulders", "Chest"):
        build.Armor[slot]["Set"] = "Self Proc Set"
    service = ExtremeActualHealGearRuntimeBuffService(
        "unused.db", repository=_Repository(), resolver=_Resolver()
    )
    result = service.resolve(
        build,
        active_bar="front",
        event=RuntimeEvent(
            time_seconds=0.0, trigger="overheal_self_or_ally", source="test"
        ),
        snapshot_time_seconds=1.0,
    )
    assert result.active_buffs == ("Major Courage",)


def test_self_or_ally_gear_proc_can_apply_to_wearer():
    class HybridResolver:
        @staticmethod
        def resolve(set_id, piece_count):
            if piece_count < 5:
                return []
            return [
                EffectVariant(
                    name="major_courage",
                    layer=EffectLayer.PROC,
                    source="fixture set",
                    duration=5.0,
                    trigger="overheal_self_or_ally",
                    target_type=SupportTargetType.SELF_OR_ALLY,
                )
            ]

    service = ExtremeActualHealGearRuntimeBuffService(
        "unused.db", repository=_Repository(), resolver=HybridResolver()
    )
    result = service.resolve(
        _five_piece("Self Proc Set"),
        active_bar="front",
        event=RuntimeEvent(time_seconds=0.0, trigger="overheal_self_or_ally", source="test"),
        snapshot_time_seconds=1.0,
    )
    assert result.active_buffs == ("Major Courage",)
    assert result.unresolved == ()


def test_conditional_gear_proc_requires_explicit_matching_context():
    class ConditionalResolver:
        @staticmethod
        def resolve(set_id, piece_count):
            if piece_count < 5:
                return []
            return [
                EffectVariant(
                    name="major_courage",
                    layer=EffectLayer.PROC,
                    source="fixture set",
                    duration=5.0,
                    trigger="overheal_self_or_ally",
                    condition="overheal_confirmed",
                    target_type=SupportTargetType.SELF,
                )
            ]

    service = ExtremeActualHealGearRuntimeBuffService(
        "unused.db", repository=_Repository(), resolver=ConditionalResolver()
    )
    kwargs = dict(
        build=_five_piece("Self Proc Set"),
        active_bar="front",
        event=RuntimeEvent(time_seconds=0.0, trigger="overheal_self_or_ally", source="test"),
        snapshot_time_seconds=1.0,
    )
    missing = service.resolve(**kwargs)
    assert missing.active_buffs == ()
    assert any("requires explicit runtime condition evidence" in item for item in missing.unresolved)

    absent = service.resolve(**kwargs, condition_context=frozenset())
    assert absent.active_buffs == ()
    assert any("condition is not satisfied" in item for item in absent.unresolved)

    proven = service.resolve(
        **kwargs, condition_context=frozenset({"overheal_confirmed"})
    )
    assert proven.active_buffs == ("Major Courage",)
    assert proven.unresolved == ()
