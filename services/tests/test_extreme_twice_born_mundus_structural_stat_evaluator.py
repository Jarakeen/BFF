from types import SimpleNamespace

from services.extreme_best_named_gear_mundus_food_potion_structural_stat_evaluator import (
    ExtremeNamedGearFiniteAxisEvaluatorFactory,
)
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)


class _MundusRepository:
    def list_names(self):
        return ("The Mage", "The Tower", "The Lord")


class _Evaluator:
    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        primary = str(kwargs.get("mundus") or "")
        secondary = str(kwargs.get("second_mundus") or "")
        score = float(bool(primary)) + float(bool(secondary))
        return score, {
            "mundus": primary,
            "second_mundus": secondary,
        }, ()


def test_twice_born_enumerates_none_singles_and_unordered_pairs():
    evaluator = ExtremeTwiceBornMundusStructuralStatEvaluator(
        evaluator=_Evaluator(),
        mundus_repository=_MundusRepository(),
    )

    states = evaluator.mundus_states()

    assert states == (
        ("", ""),
        ("The Mage", ""),
        ("The Tower", ""),
        ("The Lord", ""),
        ("The Mage", "The Tower"),
        ("The Mage", "The Lord"),
        ("The Tower", "The Lord"),
    )


def test_twice_born_search_can_choose_two_boons():
    evaluator = ExtremeTwiceBornMundusStructuralStatEvaluator(
        evaluator=_Evaluator(),
        mundus_repository=_MundusRepository(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate(
        "max_magicka",
        SimpleNamespace(),
    )

    assert value == 2.0
    assert payload["mundus"]
    assert payload["second_mundus"]
    assert payload["mundus"] != payload["second_mundus"]
    assert payload["twice_born_mundus_states_scored"] == 7
    assert unresolved == ()


def test_factory_detects_only_active_five_piece_twice_born_star():
    active = SimpleNamespace(
        set_names=("Twice-Born Star", "Other Set"),
        counts=(5, 5),
    )
    inactive = SimpleNamespace(
        set_names=("Twice-Born Star", "Other Set"),
        counts=(4, 5),
    )

    assert ExtremeNamedGearFiniteAxisEvaluatorFactory._has_active_twice_born_star(active) is True
    assert ExtremeNamedGearFiniteAxisEvaluatorFactory._has_active_twice_born_star(inactive) is False
