from __future__ import annotations

import pytest

from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationService,
)


def _counts(result):
    return dict(result.slot_counts)


def test_storm_calling_counts_all_owned_sorcerer_line_slots_for_expert_mage():
    result = ExtremeSubclassSlotAllocationService.best_allocation(
        ("storm_calling", "dark_magic", "animal_companions"),
        "spell_damage",
    )

    assert result is not None
    assert result.projected_delta == pytest.approx(648.0)
    assert _counts(result)["animal_companions"] == 0
    assert _counts(result)["storm_calling"] + _counts(result)["dark_magic"] == 6
    assert result.reviewed_sources == ("Expert Mage (6 Sorcerer slots)",)


def test_assassination_counts_all_owned_nightblade_line_slots_for_pressure_points():
    result = ExtremeSubclassSlotAllocationService.best_allocation(
        ("assassination", "shadow", "storm_calling"),
        "spell_critical",
    )

    assert result is not None
    assert _counts(result)["storm_calling"] == 0
    assert _counts(result)["assassination"] + _counts(result)["shadow"] == 6
    assert result.reviewed_sources == ("Pressure Points (6 Nightblade slots)",)


def test_animal_companions_critical_damage_is_line_scoped():
    result = ExtremeSubclassSlotAllocationService.best_allocation(
        ("animal_companions", "green_balance", "storm_calling"),
        "critical_damage",
    )

    assert result is not None
    assert result.projected_delta == pytest.approx(0.30)
    assert _counts(result)["animal_companions"] == 6
    assert result.reviewed_sources == ("Advanced Species (6 Animal Companions slots)",)


def test_winters_embrace_resistance_is_line_scoped():
    result = ExtremeSubclassSlotAllocationService.best_allocation(
        ("winters_embrace", "green_balance", "storm_calling"),
        "spell_resistance",
    )

    assert result is not None
    assert result.projected_delta == pytest.approx(7440.0)
    assert _counts(result)["winters_embrace"] == 6
    assert result.reviewed_sources == ("Frozen Armor (6 Winter's Embrace slots)",)


def test_flourish_requires_reference_value_for_percent_projection():
    assert (
        ExtremeSubclassSlotAllocationService.best_allocation(
            ("animal_companions", "green_balance", "storm_calling"),
            "magicka_recovery",
        )
        is None
    )

    result = ExtremeSubclassSlotAllocationService.best_allocation(
        ("animal_companions", "green_balance", "storm_calling"),
        "magicka_recovery",
        reference_value=1000.0,
    )
    assert result is not None
    assert result.projected_delta == pytest.approx(200.0)
    assert _counts(result)["animal_companions"] >= 1


def test_unreviewed_objective_returns_no_fake_zero_score():
    assert (
        ExtremeSubclassSlotAllocationService.best_allocation(
            ("aedric_spear", "dark_magic", "green_balance"),
            "spell_damage",
        )
        is None
    )
