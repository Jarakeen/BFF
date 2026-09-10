from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_armor_mundus_joint_objective_service import ExtremeArmorMundusPieceChoice
from services.extreme_armor_weight_trait_state_service import ExtremeArmorWeightTraitState
from services.extreme_named_gear_armor_canonical_stat_evaluator import (
    ExtremeNamedGearArmorCanonicalStatEvaluator,
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
        return 999.0, ()


class _NamedGearEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        build = PlayerBuild()
        build.Armor["Head"]["Set"] = "Monster A"
        build.Armor["Shoulders"]["Set"] = "Monster A"
        return 111.0, {
            "build": build.to_dict(),
            "gear_set_names": ("Monster A",),
        }, ()


def _candidate():
    return SimpleNamespace(
        attributes=SimpleNamespace(health=64, magicka=0, stamina=0),
        class_route=SimpleNamespace(),
        active_bar="front",
        identity=("Nord", "Dragonknight", (), 64, 0, 0, "front"),
    )


def _state(objective="physical_resistance"):
    pieces = tuple(
        ExtremeArmorMundusPieceChoice(
            slot=slot,
            weight="Heavy",
            trait="Reinforced" if slot == "Chest" else "None",
            direct_delta=1.0,
        )
        for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    )
    return ExtremeArmorWeightTraitState(
        objective_key=objective,
        pieces=pieces,
        direct_delta=7.0,
    )


def test_combined_evaluator_preserves_named_sets_and_scores_materialized_armor():
    named = _NamedGearEvaluator()
    evaluator = ExtremeNamedGearArmorCanonicalStatEvaluator(
        evaluator=named,
        armor_state=_state(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate(
        "physical_resistance",
        _candidate(),
    )

    assert value == 999.0
    assert unresolved == ()
    build = named.optimizer.last_build
    assert build.Armor["Head"]["Set"] == "Monster A"
    assert build.Armor["Shoulders"]["Set"] == "Monster A"
    assert build.Armor["Chest"]["Weight"] == "Heavy"
    assert build.Armor["Chest"]["Trait"] == "Reinforced"
    assert build.Armor["Chest"]["Quality"] == "Gold"
    assert payload["gear_set_names"] == ("Monster A",)
    assert payload["armor_heavy_pieces"] == 7
    assert payload["armor_divines_count"] == 0


def test_objective_mismatch_fails_closed_before_scoring():
    evaluator = ExtremeNamedGearArmorCanonicalStatEvaluator(
        evaluator=_NamedGearEvaluator(),
        armor_state=_state("physical_resistance"),
    )

    try:
        evaluator.evaluate_candidate("spell_resistance", _candidate())
    except ValueError as exc:
        assert "objective mismatch" in str(exc)
    else:
        raise AssertionError("expected armor-state objective mismatch to fail closed")


def test_divines_identity_is_exposed_in_combined_payload():
    pieces = tuple(
        ExtremeArmorMundusPieceChoice(
            slot=slot,
            weight="Light",
            trait="Divines",
            direct_delta=0.0,
        )
        for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    )
    state = ExtremeArmorWeightTraitState(
        objective_key="spell_resistance",
        pieces=pieces,
        direct_delta=0.0,
    )
    evaluator = ExtremeNamedGearArmorCanonicalStatEvaluator(
        evaluator=_NamedGearEvaluator(),
        armor_state=state,
    )

    _, payload, _ = evaluator.evaluate_candidate("spell_resistance", _candidate())

    assert payload["armor_light_pieces"] == 7
    assert payload["armor_divines_count"] == 7
    assert all(row[2] == "Divines" for row in payload["armor_weight_trait_state"])
