from __future__ import annotations

import pytest

from services.extreme_armor_gear_objective_service import (
    ExtremeArmorGearObjectiveService,
)


def test_resistance_piece_candidates_include_base_armor_and_static_trait_bonus():
    reinforced = ExtremeArmorGearObjectiveService.piece_candidate(
        "physical_resistance",
        slot="Chest",
        weight="Heavy",
        trait="Reinforced",
    )
    nirnhoned = ExtremeArmorGearObjectiveService.piece_candidate(
        "physical_resistance",
        slot="Chest",
        weight="Heavy",
        trait="Nirnhoned",
    )

    assert reinforced.base_armor == 2772.0
    assert reinforced.projected_delta == 3215.0
    assert nirnhoned.projected_delta == 3025.0
    assert reinforced.projected_delta > nirnhoned.projected_delta


def test_small_heavy_slots_can_prefer_nirnhoned_over_reinforced():
    hands = ExtremeArmorGearObjectiveService.best_piece_for_slot(
        "physical_resistance",
        slot="Hands",
    )
    waist = ExtremeArmorGearObjectiveService.best_piece_for_slot(
        "physical_resistance",
        slot="Waist",
    )

    assert (hands.weight, hands.trait) == ("Heavy", "Nirnhoned")
    assert (waist.weight, waist.trait) == ("Heavy", "Nirnhoned")


def test_large_heavy_slots_prefer_reinforced_for_resistance():
    for slot in ("Head", "Shoulders", "Chest", "Legs", "Feet"):
        best = ExtremeArmorGearObjectiveService.best_piece_for_slot(
            "spell_resistance",
            slot=slot,
        )
        assert (best.weight, best.trait) == ("Heavy", "Reinforced")


def test_best_seven_piece_resistance_loadout_is_all_heavy_with_slot_specific_traits():
    loadout = ExtremeArmorGearObjectiveService.best_loadout_for_objective(
        "physical_resistance"
    )

    traits = {piece.slot: piece.trait for piece in loadout.pieces}
    assert loadout.composition_label == "0L/0M/7H"
    assert loadout.projected_delta == pytest.approx(17398.0)
    assert traits == {
        "Head": "Reinforced",
        "Shoulders": "Reinforced",
        "Chest": "Reinforced",
        "Hands": "Nirnhoned",
        "Waist": "Nirnhoned",
        "Legs": "Reinforced",
        "Feet": "Reinforced",
    }


def test_invigorating_is_projected_as_armor_piece_recovery_not_armor_base_resistance():
    recovery = ExtremeArmorGearObjectiveService.piece_candidate(
        "magicka_recovery",
        slot="Head",
        weight="Heavy",
        trait="Invigorating",
    )
    plain = ExtremeArmorGearObjectiveService.piece_candidate(
        "magicka_recovery",
        slot="Head",
        weight="Heavy",
        trait="None",
    )

    assert recovery.projected_delta == 16.0
    assert plain.projected_delta == 0.0


def test_unreviewed_trait_is_rejected_instead_of_assumed_zero():
    with pytest.raises(KeyError, match="unreviewed static armor trait"):
        ExtremeArmorGearObjectiveService.piece_candidate(
            "physical_resistance",
            slot="Chest",
            weight="Heavy",
            trait="Divines",
        )


def test_unreviewed_objective_is_rejected():
    with pytest.raises(KeyError, match="unreviewed Extreme armor-gear objective"):
        ExtremeArmorGearObjectiveService.best_loadout_for_objective("critical_damage")
