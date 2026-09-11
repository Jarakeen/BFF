import pytest

from models.build_model import PlayerBuild
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightState,
    ExtremeArmorResourceWeightStateService,
)


def test_catalog_reduces_all_seven_slot_weight_loadouts_to_one_witness_per_type_count():
    catalog = ExtremeArmorResourceWeightStateService.build("max_health")

    assert catalog.denominator_proven
    assert catalog.raw_loadouts_reviewed == 3 ** 7
    assert catalog.dominated_loadouts_pruned == (3 ** 7) - 3
    assert tuple(state.armor_type_count for state in catalog.states) == (1, 2, 3)


def test_each_reduced_state_is_a_complete_legal_seven_piece_weight_witness():
    catalog = ExtremeArmorResourceWeightStateService.build("max_magicka")

    for state in catalog.states:
        assert len(state.weights) == 7
        assert state.light_pieces + state.medium_pieces + state.heavy_pieces == 7
        assert len({weight for _, weight in state.weights}) == state.armor_type_count
        assert {weight for _, weight in state.weights} <= {"Light", "Medium", "Heavy"}


def test_materialization_changes_only_weight_and_preserves_set_trait_and_glyph_axes():
    catalog = ExtremeArmorResourceWeightStateService.build("max_stamina")
    state = next(row for row in catalog.states if row.armor_type_count == 3)
    build = PlayerBuild()
    for slot in build.Armor:
        build.Armor[slot]["Set"] = "Test Set"
        build.Armor[slot]["Trait"] = "Infused"
        build.Armor[slot]["Enchant"] = "Max Stamina"
        build.Armor[slot]["Quality"] = "Gold"

    materialized = ExtremeArmorResourceWeightStateService.materialize(build, state)

    for slot in materialized.Armor:
        assert materialized.Armor[slot]["Set"] == "Test Set"
        assert materialized.Armor[slot]["Trait"] == "Infused"
        assert materialized.Armor[slot]["Enchant"] == "Max Stamina"
        assert materialized.Armor[slot]["Quality"] == "Gold"
        assert materialized.Armor[slot]["Weight"] in {"Light", "Medium", "Heavy"}


def test_unreviewed_objective_fails_closed():
    with pytest.raises(KeyError, match="unreviewed Extreme resource armor-weight objective"):
        ExtremeArmorResourceWeightStateService.build("spell_damage")


def test_materialization_rejects_incomplete_state():
    state = ExtremeArmorResourceWeightState(
        objective_key="max_health",
        weights=(("Head", "Heavy"),),
    )

    with pytest.raises(ValueError, match="does not cover all armor slots"):
        ExtremeArmorResourceWeightStateService.materialize(PlayerBuild(), state)
