from __future__ import annotations

from types import SimpleNamespace

from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphPieceChoice,
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
from services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator,
)


class _Gear:
    set_ids = (10,)
    counts = (5,)
    weapon_shape = SimpleNamespace(value="none")
    assignments = ()


class _GearResult:
    denominator_proven = True
    unresolved = ()
    realization = SimpleNamespace(
        topologies=(SimpleNamespace(realizations=(_Gear(),)),)
    )


class _Candidate:
    active_bar = "front"


def _weight(objective_key: str, count: int) -> ExtremeArmorResourceWeightState:
    weights = {
        1: (("Head", "Heavy"),),
        2: (("Head", "Heavy"), ("Chest", "Light")),
        3: (("Head", "Heavy"), ("Chest", "Light"), ("Shoulders", "Medium")),
    }[count]
    return ExtremeArmorResourceWeightState(objective_key=objective_key, weights=weights)


def _trait(objective_key: str, value: int) -> ExtremeArmorResourceTraitGlyphState:
    trait = "Divines" if value == 1 else "Infused"
    return ExtremeArmorResourceTraitGlyphState(
        objective_key=objective_key,
        pieces=(
            ExtremeArmorResourceTraitGlyphPieceChoice(
                slot="Head",
                trait=trait,
                enchant="Magicka",
                direct_delta=float(value),
            ),
        ),
        direct_glyph_delta=float(value),
    )


def _catalog(objective_key: str) -> ExtremeArmorResourceWeightTraitGlyphStateCatalog:
    weights = tuple(_weight(objective_key, count) for count in (1, 2, 3))
    traits = tuple(_trait(objective_key, value) for value in (1, 2))
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


def _factory(calls: list[tuple[int, float]]):
    def factory(_gear, armor_state):
        identity = (
            int(armor_state.armor_type_count),
            float(armor_state.trait_glyph_state.direct_glyph_delta),
        )
        calls.append(identity)

        def evaluator(_objective_key, _candidate):
            # Monotonic score is deliberately simple; the integration concern is
            # which proof-reduced armor states production chooses to evaluate.
            score = identity[0] * 100.0 + identity[1]
            return score, {"armor_identity": identity}, ()

        return evaluator

    return factory


def test_max_magicka_production_scores_only_three_type_armor_frontier() -> None:
    calls: list[tuple[int, float]] = []
    evaluator = ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_GearResult(),
        armor_catalog=_catalog("max_magicka"),
        evaluator_factory=_factory(calls),
    )

    value, payload, unresolved = evaluator("max_magicka", _Candidate())

    assert value == 302.0
    assert unresolved == ()
    assert calls == [(3, 1.0), (3, 2.0)]
    assert payload["resource_armor_states_reviewed"] == 6
    assert payload["resource_armor_states_scored"] == 2
    assert payload["resource_armor_states_pruned"] == 4
    assert payload["resource_armor_scoring_reduction_proven"] is True
    assert payload["resource_armor_retained_weight_type_count"] == 3
    assert payload["gear_resource_armor_candidates_scored"] == 2


def test_max_health_production_keeps_full_armor_denominator() -> None:
    calls: list[tuple[int, float]] = []
    evaluator = ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_GearResult(),
        armor_catalog=_catalog("max_health"),
        evaluator_factory=_factory(calls),
    )

    value, payload, unresolved = evaluator("max_health", _Candidate())

    assert value == 302.0
    assert unresolved == ()
    assert len(calls) == 6
    assert payload["resource_armor_states_reviewed"] == 6
    assert payload["resource_armor_states_scored"] == 6
    assert payload["resource_armor_states_pruned"] == 0
    assert payload["resource_armor_scoring_reduction_proven"] is False
    assert payload["resource_armor_retained_weight_type_count"] is None
    assert payload["gear_resource_armor_candidates_scored"] == 6
