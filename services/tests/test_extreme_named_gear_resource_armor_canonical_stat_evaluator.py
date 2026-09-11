from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphPieceChoice,
    ExtremeArmorResourceTraitGlyphState,
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
        return 1234.0, ()


class _NamedGearEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        build = PlayerBuild()
        build.Armor["Head"]["Set"] = "Set A"
        build.Armor["Chest"]["Set"] = "Set B"
        return 100.0, {"build": build.to_dict(), "gear_set_names": ("Set A", "Set B")}, ()


def _candidate():
    return SimpleNamespace(
        attributes=SimpleNamespace(health=64, magicka=0, stamina=0),
        class_route=SimpleNamespace(),
        active_bar="front",
        identity=("Nord", "Dragonknight", (), 64, 0, 0, "front"),
    )


def _state(objective="max_health"):
    slots = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    pieces = tuple(
        ExtremeArmorResourceTraitGlyphPieceChoice(
            slot=slot,
            trait="Infused" if slot == "Chest" else "Divines",
            enchant="Max Health",
            direct_delta=100.0,
        )
        for slot in slots
    )
    return ExtremeArmorResourceTraitGlyphState(
        objective_key=objective,
        pieces=pieces,
        direct_glyph_delta=700.0,
    )


def test_combined_evaluator_preserves_sets_and_scores_materialized_resource_armor():
    named = _NamedGearEvaluator()
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_state(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate("max_health", _candidate())

    assert value == 1234.0
    assert unresolved == ()
    build = named.optimizer.last_build
    assert build.Armor["Head"]["Set"] == "Set A"
    assert build.Armor["Chest"]["Set"] == "Set B"
    assert build.Armor["Chest"]["Trait"] == "Infused"
    assert build.Armor["Chest"]["Enchant"] == "Max Health"
    assert build.Armor["Chest"]["Quality"] == "Gold"
    assert build.Armor["Chest"]["Level"] == "CP160"
    assert build.Armor["Chest"]["EnchantTier"] == "Truly Superb"
    assert payload["armor_infused_count"] == 1
    assert payload["armor_divines_count"] == 6
    assert payload["armor_reviewed_glyph_delta"] == 700.0


def test_objective_mismatch_fails_closed():
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=_NamedGearEvaluator(),
        armor_state=_state("max_health"),
    )

    try:
        evaluator.evaluate_candidate("max_magicka", _candidate())
    except ValueError as exc:
        assert "objective mismatch" in str(exc)
    else:
        raise AssertionError("expected resource armor objective mismatch to fail closed")
