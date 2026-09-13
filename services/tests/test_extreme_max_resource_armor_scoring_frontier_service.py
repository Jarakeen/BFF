from __future__ import annotations

from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphState,
    ExtremeArmorResourceTraitGlyphStateCatalog,
)
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightState,
    ExtremeArmorResourceWeightStateCatalog,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
    ExtremeArmorResourceWeightTraitGlyphStateCatalog,
)
from services.extreme_max_resource_armor_scoring_frontier_service import (
    ExtremeMaxResourceArmorScoringFrontierService,
)


def _weight(objective_key: str, count: int) -> ExtremeArmorResourceWeightState:
    weights = {
        1: (("Head", "Heavy"),),
        2: (("Head", "Heavy"), ("Chest", "Light")),
        3: (("Head", "Heavy"), ("Chest", "Light"), ("Shoulders", "Medium")),
    }[count]
    return ExtremeArmorResourceWeightState(objective_key=objective_key, weights=weights)


def _trait(objective_key: str, divines: int) -> ExtremeArmorResourceTraitGlyphState:
    # Identity is all this service needs; the source trait/glyph reducer owns the
    # actual piece-level proof and canonical materialization.
    return ExtremeArmorResourceTraitGlyphState(
        objective_key=objective_key,
        pieces=(),
        direct_glyph_delta=float(divines),
    )


def _catalog(objective_key: str = "max_magicka") -> ExtremeArmorResourceWeightTraitGlyphStateCatalog:
    weights = tuple(_weight(objective_key, count) for count in (1, 2, 3))
    traits = tuple(_trait(objective_key, count) for count in range(2))
    weight_catalog = ExtremeArmorResourceWeightStateCatalog(
        objective_key=objective_key,
        states=weights,
        raw_loadouts_reviewed=3,
        dominated_loadouts_pruned=0,
        unresolved=(),
    )
    trait_catalog = ExtremeArmorResourceTraitGlyphStateCatalog(
        objective_key=objective_key,
        states=traits,
        glyph_choices_reviewed=1,
        raw_piece_choices_reviewed=1,
        dominated_states_pruned=0,
        unresolved=(),
    )
    states = tuple(
        ExtremeArmorResourceWeightTraitGlyphState(
            objective_key=objective_key,
            weight_state=weight,
            trait_glyph_state=trait,
        )
        for weight in weights
        for trait in traits
    )
    return ExtremeArmorResourceWeightTraitGlyphStateCatalog(
        objective_key=objective_key,
        states=states,
        weight_catalog=weight_catalog,
        trait_glyph_catalog=trait_catalog,
        unresolved=(),
    )


def test_magicka_frontier_keeps_only_three_type_weight_witnesses() -> None:
    result = ExtremeMaxResourceArmorScoringFrontierService.build(
        "max_magicka",
        _catalog(),
    )

    assert result.reduction_proven is True
    assert result.source_state_count == 6
    assert len(result.states) == 2
    assert result.states_pruned == 4
    assert all(state.armor_type_count == 3 for state in result.states)


def test_stamina_frontier_uses_same_monotonic_undaunted_proof() -> None:
    result = ExtremeMaxResourceArmorScoringFrontierService.build(
        "max_stamina",
        _catalog("max_stamina"),
    )

    assert result.reduction_proven is True
    assert len(result.states) == 2


def test_max_health_is_not_reduced_by_this_frontier() -> None:
    try:
        ExtremeMaxResourceArmorScoringFrontierService.build(
            "max_health",
            _catalog("max_health"),
        )
    except KeyError as exc:
        assert "unreviewed Extreme max-resource armor scoring frontier objective" in str(exc)
    else:
        raise AssertionError("max_health must not use Magicka/Stamina armor dominance")


def test_incomplete_source_denominator_fails_closed() -> None:
    catalog = _catalog()
    broken_weight_catalog = ExtremeArmorResourceWeightStateCatalog(
        objective_key="max_magicka",
        states=catalog.weight_catalog.states[:2],
        raw_loadouts_reviewed=2,
        dominated_loadouts_pruned=0,
        unresolved=(),
    )
    broken = ExtremeArmorResourceWeightTraitGlyphStateCatalog(
        objective_key="max_magicka",
        states=tuple(
            state for state in catalog.states if state.armor_type_count < 3
        ),
        weight_catalog=broken_weight_catalog,
        trait_glyph_catalog=catalog.trait_glyph_catalog,
        unresolved=(),
    )

    result = ExtremeMaxResourceArmorScoringFrontierService.build(
        "max_magicka",
        broken,
    )

    assert result.reduction_proven is False
    assert result.unresolved
