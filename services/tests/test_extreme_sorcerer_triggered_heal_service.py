from __future__ import annotations

import pytest

from minmax.skill_component_classification import HealRecipientScope, HealTemporalScope
from services.extreme_sorcerer_triggered_heal_service import (
    ExtremeSorcererTriggeredHealService,
)


def test_dark_conversion_is_direct_self_heal_but_value_requires_noncoefficient_resolution():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Dark Conversion",
    )

    assert result.trigger_satisfied is True
    assert result.recipient_scope is HealRecipientScope.SELF
    assert result.temporal_scope is HealTemporalScope.DIRECT
    assert result.normal_heal is None
    assert result.can_crit is None
    assert result.unresolved


def test_dark_deal_accepts_explicit_resolved_heal_value():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Dark Deal",
        resolved_heal_amount=8123.0,
    )

    assert result.complete is True
    assert result.normal_heal == pytest.approx(8123.0)


def test_critical_surge_requires_active_window_and_critical_damage_trigger():
    service = ExtremeSorcererTriggeredHealService()

    inactive = service.resolve(
        ability_name="Critical Surge",
        surge_window_active=True,
        critical_damage_triggered=False,
        resolved_heal_amount=3300.0,
    )
    active = service.resolve(
        ability_name="Critical Surge",
        surge_window_active=True,
        critical_damage_triggered=True,
        resolved_heal_amount=3300.0,
    )

    assert inactive.trigger_satisfied is False
    assert inactive.normal_heal is None
    assert active.trigger_satisfied is True
    assert active.normal_heal == pytest.approx(3300.0)
    assert active.cooldown_seconds == pytest.approx(1.0)
    assert active.recipient_scope is HealRecipientScope.SELF


def test_power_surge_uses_critical_heal_trigger_and_group_recipient_scope():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Power Surge",
        surge_window_active=True,
        critical_heal_triggered=True,
        resolved_heal_amount=2550.0,
    )

    assert result.trigger_satisfied is True
    assert result.trigger_kind == "critical_heal_while_power_surge_active"
    assert result.recipient_scope is HealRecipientScope.GROUP
    assert result.temporal_scope is HealTemporalScope.DIRECT
    assert result.cooldown_seconds == pytest.approx(3.0)
    assert result.normal_heal == pytest.approx(2550.0)


def test_power_surge_does_not_trigger_from_critical_damage():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Power Surge",
        surge_window_active=True,
        critical_damage_triggered=True,
        critical_heal_triggered=False,
        resolved_heal_amount=2550.0,
    )

    assert result.trigger_satisfied is False
    assert result.normal_heal is None


def test_blood_magic_rank_two_heals_ten_percent_max_health_below_full_health():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Blood Magic",
        dark_magic_ability_cast_with_cost=True,
        caster_at_full_health=False,
        max_health=32100.0,
    )

    assert result.complete is True
    assert result.normal_heal == pytest.approx(3210.0)
    assert result.recipient_scope is HealRecipientScope.SELF
    assert result.temporal_scope is HealTemporalScope.DIRECT
    assert result.can_crit is False


def test_blood_magic_full_health_branch_emits_no_heal_event_but_preserves_noncritical_policy():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Blood Magic",
        dark_magic_ability_cast_with_cost=True,
        caster_at_full_health=True,
        max_health=32100.0,
    )

    assert result.trigger_satisfied is False
    assert result.normal_heal is None
    assert result.can_crit is False
    assert result.unresolved == ()


def test_blood_magic_requires_max_health_when_triggered():
    result = ExtremeSorcererTriggeredHealService().resolve(
        ability_name="Blood Magic",
        dark_magic_ability_cast_with_cost=True,
        caster_at_full_health=False,
    )

    assert result.trigger_satisfied is True
    assert result.normal_heal is None
    assert result.can_crit is False
    assert result.unresolved == ("Blood Magic U50 rank-2 healing requires Max Health",)


def test_negative_resolved_heal_amount_is_rejected():
    with pytest.raises(ValueError, match="resolved_heal_amount"):
        ExtremeSorcererTriggeredHealService().resolve(
            ability_name="Critical Surge",
            surge_window_active=True,
            critical_damage_triggered=True,
            resolved_heal_amount=-1,
        )
