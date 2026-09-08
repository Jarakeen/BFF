from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_critical_healing_cap_service import ExtremeCriticalHealingCapService
from services.extreme_healing_event_service import ExtremeHealingEventResult


def _event(*, normal, critical, bonus, multiplier, unresolved=()):
    return ExtremeHealingEventResult(
        entity_id="test_heal",
        normal_heal=normal,
        critical_heal=critical,
        critical_healing_bonus=bonus,
        critical_multiplier=multiplier,
        heal_coefficient_numbers=(1, 2),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(2,),
        tooltip_result=SimpleNamespace(),
        unresolved=tuple(unresolved),
    )


def test_under_cap_event_keeps_existing_critical_value():
    event = _event(normal=1500.0, critical=2200.0, bonus=0.20, multiplier=1.70)

    result = ExtremeCriticalHealingCapService().apply(event)

    assert result.event.critical_heal == pytest.approx(2200.0)
    assert result.event.critical_multiplier == pytest.approx(1.70)
    assert result.effective_critical_bonus == pytest.approx(0.20)
    assert result.capped is False


def test_ordinary_critical_healing_is_capped_at_125_percent_bonus():
    # 1000 crit-eligible + 500 noncrit. The incoming event was calculated with
    # 150% total crit bonus (2.50x), which exceeds the ordinary 125% ceiling.
    event = _event(normal=1500.0, critical=3000.0, bonus=1.00, multiplier=2.50)

    result = ExtremeCriticalHealingCapService().apply(event)

    assert result.event.critical_multiplier == pytest.approx(2.25)
    assert result.event.critical_healing_bonus == pytest.approx(0.75)
    assert result.event.critical_heal == pytest.approx(2750.0)
    assert result.capped is True


def test_above_and_beyond_raises_cap_and_adds_critical_healing():
    # Existing: 1000 crit-eligible + 500 noncrit at 100% total crit bonus.
    event = _event(normal=1500.0, critical=2500.0, bonus=0.50, multiplier=2.00)

    result = ExtremeCriticalHealingCapService().apply(
        event,
        additional_critical_healing=0.25,
        critical_healing_cap=1.55,
    )

    assert result.event.critical_multiplier == pytest.approx(2.25)
    assert result.event.critical_healing_bonus == pytest.approx(0.75)
    assert result.event.critical_heal == pytest.approx(2750.0)
    assert result.capped is False


def test_above_and_beyond_still_caps_excessive_critical_healing_at_155_percent_bonus():
    event = _event(normal=1500.0, critical=3200.0, bonus=1.20, multiplier=2.70)

    result = ExtremeCriticalHealingCapService().apply(
        event,
        additional_critical_healing=0.25,
        critical_healing_cap=1.55,
    )

    assert result.event.critical_multiplier == pytest.approx(2.55)
    assert result.event.critical_healing_bonus == pytest.approx(1.05)
    assert result.event.critical_heal == pytest.approx(3050.0)
    assert result.capped is True


def test_mixed_event_does_not_apply_critical_bonus_to_noncrittable_component():
    # 800 crit-eligible + 400 noncrit. Existing multiplier is 1.50.
    event = _event(normal=1200.0, critical=1600.0, bonus=0.0, multiplier=1.50)

    result = ExtremeCriticalHealingCapService().apply(
        event,
        additional_critical_healing=0.25,
        critical_healing_cap=1.55,
    )

    assert result.event.critical_multiplier == pytest.approx(1.75)
    assert result.event.critical_heal == pytest.approx(1800.0)


def test_unresolved_numeric_event_preserves_unresolved_state_while_updating_cap_metadata():
    event = _event(
        normal=None,
        critical=None,
        bonus=0.90,
        multiplier=2.40,
        unresolved=("recipient scope unresolved",),
    )

    result = ExtremeCriticalHealingCapService().apply(event)

    assert result.event.normal_heal is None
    assert result.event.critical_heal is None
    assert result.event.critical_multiplier == pytest.approx(2.25)
    assert result.event.critical_healing_bonus == pytest.approx(0.75)
    assert result.event.unresolved == ("recipient scope unresolved",)
    assert result.capped is True


def test_invalid_cap_below_base_critical_healing_is_rejected():
    event = _event(normal=1000.0, critical=1500.0, bonus=0.0, multiplier=1.50)

    with pytest.raises(ValueError, match="cannot be below base"):
        ExtremeCriticalHealingCapService().apply(event, critical_healing_cap=0.49)


def test_negative_additional_critical_healing_is_rejected():
    event = _event(normal=1000.0, critical=1500.0, bonus=0.0, multiplier=1.50)

    with pytest.raises(ValueError, match="cannot be negative"):
        ExtremeCriticalHealingCapService().apply(
            event,
            additional_critical_healing=-0.01,
        )
