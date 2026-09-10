from models.build_model import PlayerBuild
from services.extreme_armor_weight_trait_state_service import (
    ExtremeArmorWeightTraitState,
    ExtremeArmorWeightTraitStateService,
)
from services.extreme_armor_mundus_joint_objective_service import ExtremeArmorMundusPieceChoice


def test_reviewed_objective_exposes_deterministic_seven_piece_states():
    catalog = ExtremeArmorWeightTraitStateService.build("physical_resistance")

    assert catalog.reviewed_source_denominator_proven is True
    assert catalog.reviewed_traits == (
        "None", "Divines", "Reinforced", "Nirnhoned", "Invigorating"
    )
    assert catalog.states
    assert all(len(state.pieces) == 7 for state in catalog.states)
    assert tuple(state.identity for state in catalog.states) == tuple(
        sorted(state.identity for state in catalog.states)
    )


def test_state_retains_weight_and_divines_count_evidence():
    catalog = ExtremeArmorWeightTraitStateService.build("spell_resistance")
    state = next(row for row in catalog.states if row.divines_count > 0)

    assert state.light_pieces + state.medium_pieces + state.heavy_pieces == 7
    assert state.divines_count == sum(
        1 for piece in state.pieces if piece.trait == "Divines"
    )


def test_materializer_preserves_named_set_and_enchant_identity():
    build = PlayerBuild()
    build.Armor["Head"]["Set"] = "Trial Set"
    build.Armor["Head"]["Enchant"] = "Max Health"
    pieces = tuple(
        ExtremeArmorMundusPieceChoice(
            slot=slot,
            weight="Heavy" if slot == "Chest" else "Light",
            trait="Divines" if slot == "Head" else "None",
            direct_delta=0.0,
        )
        for slot in build.Armor
    )
    state = ExtremeArmorWeightTraitState(
        objective_key="physical_resistance",
        pieces=pieces,
        direct_delta=0.0,
    )

    result = ExtremeArmorWeightTraitStateService.materialize(build, state)

    assert result.Armor["Head"]["Set"] == "Trial Set"
    assert result.Armor["Head"]["Enchant"] == "Max Health"
    assert result.Armor["Head"]["Trait"] == "Divines"
    assert result.Armor["Head"]["Quality"] == "Gold"
    assert result.Armor["Chest"]["Weight"] == "Heavy"
    assert result.Armor["Shoulders"]["Trait"] == ""


def test_materializer_requires_all_seven_armor_slots():
    state = ExtremeArmorWeightTraitState(
        objective_key="physical_resistance",
        pieces=(
            ExtremeArmorMundusPieceChoice(
                slot="Head", weight="Heavy", trait="Reinforced", direct_delta=0.0
            ),
        ),
        direct_delta=0.0,
    )

    try:
        ExtremeArmorWeightTraitStateService.materialize(PlayerBuild(), state)
    except ValueError as exc:
        assert "does not cover all armor slots" in str(exc)
    else:
        raise AssertionError("expected incomplete armor state to fail closed")


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeArmorWeightTraitStateService.build("max_health")
    except KeyError as exc:
        assert "unreviewed Extreme armor weight/trait objective" in str(exc)
    else:
        raise AssertionError("expected unreviewed armor objective to fail closed")
