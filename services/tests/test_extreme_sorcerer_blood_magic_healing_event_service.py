from __future__ import annotations

from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.runtime_event import RuntimeEvent
from minmax.stat_ids import StatId
from services.extreme_sorcerer_blood_magic_healing_event_service import (
    ExtremeSorcererBloodMagicHealingEventService,
)


def _context(
    *,
    healing_done=0.0,
    healing_taken=0.0,
    critical_healing=0.0,
    active_buffs=(),
):
    derived = {
        StatId.HEALING_DONE: SimpleNamespace(final_value=healing_done),
        StatId.HEALING_TAKEN: SimpleNamespace(final_value=healing_taken),
        StatId.CRITICAL_HEALING: SimpleNamespace(final_value=critical_healing),
    }
    return SimpleNamespace(
        core_state=SimpleNamespace(derived=derived),
        combat_state=CombatState(active_buffs=tuple(active_buffs)),
    )


def _event():
    return RuntimeEvent(
        time_seconds=3.0,
        trigger="cast",
        source="Dark Exchange",
    )


def test_blood_magic_self_heal_emits_caster_owned_triggered_event():
    result = ExtremeSorcererBloodMagicHealingEventService().resolve(
        context=_context(),
        trigger_event=_event(),
        base_self_heal=1600.0,
    )

    assert result.mechanic_complete
    assert result.normal_event is not None
    assert result.normal_event.source == "Sorcerer: Blood Magic"
    assert result.normal_event.target == "self"
    assert result.normal_event.time_seconds == 3.0
    assert result.normal_heal == 1600.0
    assert result.normal_event.amount == 1600.0
    assert result.critical_heal == 2400.0
    assert result.critical_multiplier == 1.5
    assert result.healing_received_ratio_points == 0.0
    assert result.healing_received_sources == ()


def test_blood_magic_self_heal_uses_healing_done_taken_and_critical_healing():
    result = ExtremeSorcererBloodMagicHealingEventService().resolve(
        context=_context(
            healing_done=0.20,
            healing_taken=0.10,
            critical_healing=0.25,
        ),
        trigger_event=_event(),
        base_self_heal=1600.0,
    )

    expected_normal = 1600.0 * 1.20 * 1.10
    assert result.normal_heal == expected_normal
    assert result.critical_multiplier == 1.75
    assert result.critical_heal == expected_normal * 1.75


def test_blood_magic_self_heal_applies_vitality_as_healing_received():
    result = ExtremeSorcererBloodMagicHealingEventService().resolve(
        context=_context(active_buffs=("Minor Vitality", "Major Vitality")),
        trigger_event=_event(),
        base_self_heal=1600.0,
    )

    assert result.healing_received_ratio_points == 0.18
    assert result.healing_received_sources == ("Minor Vitality", "Major Vitality")
    assert result.normal_heal == 1600.0 * 1.18
    assert result.critical_heal == 1600.0 * 1.18 * 1.5


def test_blood_magic_self_heal_applies_defile_as_negative_healing_received():
    result = ExtremeSorcererBloodMagicHealingEventService().resolve(
        context=_context(active_buffs=("Minor Defile", "Major Defile")),
        trigger_event=_event(),
        base_self_heal=1600.0,
    )

    assert result.healing_received_ratio_points == -0.18
    assert result.healing_received_sources == ("Minor Defile", "Major Defile")
    assert result.normal_heal == 1600.0 * 0.82
    assert result.critical_heal == 1600.0 * 0.82 * 1.5


def test_blood_magic_self_heal_respects_ordinary_critical_healing_cap():
    result = ExtremeSorcererBloodMagicHealingEventService().resolve(
        context=_context(critical_healing=2.0),
        trigger_event=_event(),
        base_self_heal=1600.0,
    )

    assert result.critical_healing_bonus == 0.75
    assert result.critical_multiplier == 2.25
    assert result.critical_heal == 3600.0


def test_blood_magic_self_heal_fails_closed_without_canonical_core_state():
    result = ExtremeSorcererBloodMagicHealingEventService().resolve(
        context=SimpleNamespace(core_state=None),
        trigger_event=_event(),
        base_self_heal=1600.0,
    )

    assert not result.mechanic_complete
    assert result.normal_event is None
    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("core_state" in message for message in result.unresolved)
