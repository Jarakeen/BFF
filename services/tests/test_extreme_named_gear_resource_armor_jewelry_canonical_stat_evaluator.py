from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphPieceChoice,
    ExtremeArmorResourceTraitGlyphState,
)
from services.extreme_armor_resource_weight_state_service import ExtremeArmorResourceWeightState
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitState,
)
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)


class _ProgressionService:
    def normalize(self, progression, route):
        return progression


class _Optimizer:
    def __init__(self):
        self.last_build = None

    def objective(self, key):
        return SimpleNamespace(key=key)

    def _evaluate(self, build, **kwargs):
        self.last_build = build
        return 54321.0, ()


class _NamedGearEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        build = PlayerBuild()
        build.Necklace.Set = "Set A"
        build.Ring1.Set = "Set B"
        build.Ring2.Set = "Set B"
        return 100.0, {"build": build.to_dict()}, ()


def _candidate():
    return SimpleNamespace(
        attributes=SimpleNamespace(health=64, magicka=0, stamina=0),
        class_route=SimpleNamespace(),
        active_bar="front",
        identity=("Nord", "Dragonknight", (), 64, 0, 0, "front"),
    )


def _armor_state():
    slots = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    trait_glyph = ExtremeArmorResourceTraitGlyphState(
        objective_key="max_health",
        pieces=tuple(
            ExtremeArmorResourceTraitGlyphPieceChoice(
                slot=slot,
                trait="Divines",
                enchant="Max Health",
                direct_delta=100.0,
            )
            for slot in slots
        ),
        direct_glyph_delta=700.0,
    )
    weight = ExtremeArmorResourceWeightState(
        objective_key="max_health",
        weights=tuple((slot, "Heavy") for slot in slots),
    )
    return ExtremeArmorResourceWeightTraitGlyphState(
        objective_key="max_health",
        weight_state=weight,
        trait_glyph_state=trait_glyph,
    )


def _jewelry_state(objective="max_health"):
    return ExtremeJewelryResourceStaticTraitState(
        objective_key=objective,
        traits=(
            ("Necklace", "Healthy"),
            ("Ring1", "Healthy"),
            ("Ring2", "Healthy"),
        ),
        direct_delta=2895.0,
    )


def test_reviewed_jewelry_traits_preserve_sets_and_reach_canonical_scoring():
    named = _NamedGearEvaluator()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_armor_state(),
        jewelry_state=_jewelry_state(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate("max_health", _candidate())

    assert value == 54321.0
    assert unresolved == ()
    build = named.optimizer.last_build
    assert build.Necklace.Set == "Set A"
    assert build.Ring1.Set == "Set B"
    assert build.Ring2.Set == "Set B"
    assert build.Necklace.Trait == "Healthy"
    assert build.Ring1.Trait == "Healthy"
    assert build.Ring2.Trait == "Healthy"
    assert build.Necklace.Quality == "Gold"
    assert build.Ring1.Level == "CP160"
    assert payload["jewelry_resource_static_trait_state"] == _jewelry_state().identity
    assert payload["jewelry_reviewed_static_trait_delta"] == 2895.0


def test_jewelry_objective_mismatch_fails_closed():
    try:
        ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
            evaluator=_NamedGearEvaluator(),
            armor_state=_armor_state(),
            jewelry_state=_jewelry_state("max_magicka"),
        )
    except ValueError as exc:
        assert "jewelry/armor objective mismatch" in str(exc)
    else:
        raise AssertionError("expected jewelry/armor objective mismatch to fail closed")
