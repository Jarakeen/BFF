from __future__ import annotations

from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.runtime_event import RuntimeEvent
from minmax.stat_ids import StatId
from services.extreme_warden_bond_with_nature_healing_event_service import (
    ExtremeWardenBondWithNatureHealingEventService,
)


def _context(
    *,
    healing_done=0.0,
    healing_taken=0.0,
    critical_healing=0.0,
    active_buffs=(),
):
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.HEALING_DONE: SimpleNamespace(final_value=healing_done),
                StatId.HEALING_TAKEN: SimpleNamespace(final_value=healing_taken),
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=critical_healing),
            }
        ),
        combat_state=CombatState(active_buffs=tuple(active_buffs)),
    )


def _event():
    return RuntimeEvent(
        time_seconds=5.0,
        trigger="effect_ended",
        source="Blue Betty",
    )


def test_bond_with_nature_emits_caster_owned_triggered_heal():
    result = ExtremeWardenBondWithNatureHealingEventService().resolve(
        context=_context(),
        trigger_event=_event(),
        base_self_heal=1530.0,
    )

    assert result.mechanic_complete
    assert result.normal_event is not None
    assert result.normal_event.source == "Warden: Bond with Nature"
    assert result.normal_event.target == "self"
    assert result.normal_event.time_seconds == 5.0
    assert result.normal_heal == 1530.0
    assert result.critical_heal == 2295.0
    assert result.critical_multiplier == 1.5


def test_bond_with_nature_uses_canonical_healing_modifiers():
    result = ExtremeWardenBondWithNatureHealingEventService().resolve(
        context=_context(
            healing_done=0.20,
            healing_taken=0.10,
            critical_healing=0.25,
        ),
        trigger_event=_event(),
        base_self_heal=1530.0,
    )

    expected_normal = 1530.0 * 1.20 * 1.10
    assert result.normal_heal == expected_normal
    assert result.critical_multiplier == 1.75
    assert result.critical_heal == expected_normal * 1.75


def test_bond_with_nature_applies_recipient_vitality():
    result = ExtremeWardenBondWithNatureHealingEventService().resolve(
        context=_context(active_buffs=("Minor Vitality", "Major Vitality")),
        trigger_event=_event(),
        base_self_heal=1530.0,
    )

    assert result.healing_received_ratio_points == 0.18
    assert result.normal_heal == 1530.0 * 1.18


def test_bond_with_nature_respects_ordinary_critical_healing_cap():
    result = ExtremeWardenBondWithNatureHealingEventService().resolve(
        context=_context(critical_healing=2.0),
        trigger_event=_event(),
        base_self_heal=1530.0,
    )

    assert result.critical_healing_bonus == 0.75
    assert result.critical_multiplier == 2.25
    assert result.critical_heal == 1530.0 * 2.25


def test_bond_with_nature_fails_closed_without_canonical_core_state():
    result = ExtremeWardenBondWithNatureHealingEventService().resolve(
        context=SimpleNamespace(core_state=None),
        trigger_event=_event(),
        base_self_heal=1530.0,
    )

    assert not result.mechanic_complete
    assert result.normal_event is None
    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("core_state" in message for message in result.unresolved)
