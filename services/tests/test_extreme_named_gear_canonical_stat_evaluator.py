from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation
from models.build_model import PlayerBuild
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_canonical_stat_evaluator import ExtremeNamedGearCanonicalStatEvaluator
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


class _ProgressionService:
    def normalize(self, progression, class_route):
        return progression


class _Optimizer:
    def objective(self, key):
        return SimpleNamespace(key=key)

    def _evaluate(self, build, **kwargs):
        # The score deliberately depends on materialized named gear, proving the
        # bridge re-scores the completed PlayerBuild instead of returning the
        # wrapped structural evaluator's original value.
        body = sum(1 for row in build.Armor.values() if row.get("Set") == "Five A")
        weapon = 2 if build.FrontBarWeapon.Set == "Arena Staff" else 0
        return float(body + weapon), ()


class _BaseEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        build = PlayerBuild(Name="Base", Race="Breton", EsoClass="Warden")
        return 999.0, {
            "build": build.to_dict(),
            "race": "Breton",
            "mundus": kwargs.get("mundus", ""),
            "food": kwargs.get("food", ""),
            "potion": kwargs.get("potion", ""),
            "active_buffs": tuple(kwargs.get("active_buffs", ())),
        }, ()


def _realization():
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2|unused:5",
        set_ids=(10, 30),
        set_names=("Five A", "Arena Staff"),
        counts=(5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Shoulders", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Chest", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Hands", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Waist", 10, "Five A"),
            ExtremeNamedGearSlotAssignment("Main Hand", 30, "Arena Staff", "Inferno Staff"),
        ),
    )


def test_named_gear_wrapper_materializes_then_rescores_canonical_build():
    base = _BaseEvaluator()
    evaluator = ExtremeNamedGearCanonicalStatEvaluator(
        evaluator=base,
        realization=_realization(),
    )
    candidate = SimpleNamespace(
        attributes=AttributeAllocation(health=0, magicka=64, stamina=0),
        class_route=object(),
        active_bar="front",
        identity=("Breton", "Warden", (), 0, 64, 0, "front"),
    )

    value, payload, unresolved = evaluator.evaluate_candidate(
        "max_magicka",
        candidate,
        mundus="The Mage",
        food="Test Food",
        potion="test_potion",
    )

    assert value == 7.0
    assert unresolved == ()
    assert payload["gear_topology"] == "5+2|unused:5"
    assert payload["gear_set_names"] == ("Five A", "Arena Staff")
    assert payload["build"]["Armor"]["Head"]["Set"] == "Five A"
    assert payload["build"]["FrontBarWeapon"]["Set"] == "Arena Staff"
    assert payload["mundus"] == "The Mage"
    assert payload["food"] == "Test Food"
    assert payload["potion"] == "test_potion"
