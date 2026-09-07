from __future__ import annotations

import pytest

from services.extreme_novelty_objective_catalog import (
    BASH_COST,
    BASH_DAMAGE,
    CRITICAL_HEALING,
    DETECTION_RADIUS_REDUCTION,
    HEALING_DONE,
    HEALING_OUTPUT,
    MOST_BASHY,
    MOST_SNEAKY,
    MOST_STAMINA_HEALER,
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


def test_most_stamina_healer_is_genuinely_stamina_primary_and_healer_scoped():
    assert MOST_STAMINA_HEALER.primary is HEALING_OUTPUT
    assert MOST_STAMINA_HEALER.primary.direction is ExtremeObjectiveDirection.MAXIMIZE
    assert MOST_STAMINA_HEALER.secondary == (HEALING_DONE, CRITICAL_HEALING)
    assert MOST_STAMINA_HEALER.required_primary_resource == "stamina"
    assert MOST_STAMINA_HEALER.required_role == "healer"


def test_stamina_healer_explicitly_explores_healing_vault_without_hard_requiring_it():
    assert MOST_STAMINA_HEALER.required_front_weapon_family is None
    assert MOST_STAMINA_HEALER.required_back_weapon_family is None
    assert len(MOST_STAMINA_HEALER.preferred_scribed_routes) == 1

    route = MOST_STAMINA_HEALER.preferred_scribed_routes[0]
    assert route.weapon_family == "bow"
    assert route.grimoire == "Vault"
    assert route.focus == "Healing"
    assert route.signature == "Sage's Remedy"
    assert "preferred candidate" in route.note.casefold()
    assert "hard requirement" in route.note.casefold()


def test_catalog_exposes_all_named_novelty_recipes():
    assert [recipe.key for recipe in ExtremeNoveltyObjectiveCatalog.all_recipes()] == [
        "most_sneaky",
        "most_bashy",
        "most_stamina_healer",
    ]
    assert ExtremeNoveltyObjectiveCatalog.get(" MOST_BASHY ") is MOST_BASHY
    assert (
        ExtremeNoveltyObjectiveCatalog.get("most_stamina_healer")
        is MOST_STAMINA_HEALER
    )


def test_unknown_novelty_recipe_is_rejected():
    with pytest.raises(KeyError, match="unknown Extreme novelty recipe"):
        ExtremeNoveltyObjectiveCatalog.get("most_tax_accounting")
