from __future__ import annotations

import pytest

from services.extreme_novelty_objective_catalog import (
    BASH_COST,
    BASH_DAMAGE,
    DETECTION_RADIUS_REDUCTION,
    MOST_BASHY,
    MOST_SNEAKY,
    SNEAK_COST_REDUCTION,
    ExtremeNoveltyObjectiveCatalog,
    ExtremeObjectiveDirection,
)


def test_most_sneaky_prioritizes_detection_then_sneak_cost():
    assert MOST_SNEAKY.primary is DETECTION_RADIUS_REDUCTION
    assert MOST_SNEAKY.primary.direction is ExtremeObjectiveDirection.MAXIMIZE
    assert MOST_SNEAKY.secondary == (SNEAK_COST_REDUCTION,)
    assert SNEAK_COST_REDUCTION.direction is ExtremeObjectiveDirection.MAXIMIZE
    assert MOST_SNEAKY.required_front_weapon_family is None
    assert MOST_SNEAKY.required_back_weapon_family is None


def test_most_bashy_requires_sword_and_board_on_both_bars():
    assert MOST_BASHY.primary is BASH_DAMAGE
    assert MOST_BASHY.primary.direction is ExtremeObjectiveDirection.MAXIMIZE
    assert MOST_BASHY.secondary == (BASH_COST,)
    assert BASH_COST.direction is ExtremeObjectiveDirection.MINIMIZE
    assert MOST_BASHY.required_front_weapon_family == "one_hand_and_shield"
    assert MOST_BASHY.required_back_weapon_family == "one_hand_and_shield"


def test_catalog_exposes_both_named_novelty_recipes():
    assert [recipe.key for recipe in ExtremeNoveltyObjectiveCatalog.all_recipes()] == [
        "most_sneaky",
        "most_bashy",
    ]
    assert ExtremeNoveltyObjectiveCatalog.get(" MOST_BASHY ") is MOST_BASHY


def test_unknown_novelty_recipe_is_rejected():
    with pytest.raises(KeyError, match="unknown Extreme novelty recipe"):
        ExtremeNoveltyObjectiveCatalog.get("most_tax_accounting")
