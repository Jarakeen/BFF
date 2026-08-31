import pytest

from minmax.resource_cost_modifiers import (
    ActionCostModifier,
    ActionCostModifierSet,
    CostModifierOperation,
)
from minmax.resource_costs import ResourceType, resolve_base_action_cost


def _cost(*, ability_id=100, base_cost=2700, base_mechanic=1):
    return resolve_base_action_cost(
        ability_id=ability_id,
        base_cost=base_cost,
        base_mechanic=base_mechanic,
        rank=4,
        morph=1,
    )


def test_resource_specific_modifier_matches_only_target_resource():
    modifier = ActionCostModifier(
        source="Glyph of Reduce Spell Cost",
        operation=CostModifierOperation.FLAT_REDUCTION,
        value=203,
        resources=(ResourceType.MAGICKA,),
    )

    assert modifier.applies_to(_cost(base_mechanic=1))
    assert not modifier.applies_to(_cost(base_mechanic=4))


def test_compound_cost_matches_modifier_for_either_consumed_resource():
    molten_whip = _cost(ability_id=20805, base_cost=1148, base_mechanic=5)
    stamina_modifier = ActionCostModifier(
        source="Stamina cost example",
        operation=CostModifierOperation.PERCENT_REDUCTION,
        value=0.05,
        resources=(ResourceType.STAMINA,),
    )

    assert stamina_modifier.applies_to(molten_whip)


def test_skill_line_scope_is_case_insensitive_and_explicit():
    modifier = ActionCostModifier(
        source="Weapon passive",
        operation=CostModifierOperation.PERCENT_REDUCTION,
        value=0.10,
        resources=(ResourceType.STAMINA,),
        skill_lines=("Bow",),
    )
    bow_cost = _cost(base_mechanic=4)

    assert modifier.applies_to(bow_cost, skill_line="bow")
    assert not modifier.applies_to(bow_cost, skill_line="Dual Wield")
    assert not modifier.applies_to(bow_cost)


def test_ability_scope_can_target_one_resolved_ability():
    modifier = ActionCostModifier(
        source="Ability-specific modifier",
        operation=CostModifierOperation.PERCENT_INCREASE,
        value=0.50,
        resources=(ResourceType.MAGICKA,),
        ability_ids=(46340,),
    )

    assert modifier.applies_to(_cost(ability_id=46340))
    assert not modifier.applies_to(_cost(ability_id=46341))


def test_modifier_set_preserves_order_and_provenance():
    first = ActionCostModifier(
        source="First",
        operation=CostModifierOperation.FLAT_REDUCTION,
        value=100,
        resources=(ResourceType.MAGICKA,),
    )
    second = ActionCostModifier(
        source="Second",
        operation=CostModifierOperation.PERCENT_REDUCTION,
        value=0.07,
        resources=(ResourceType.MAGICKA,),
    )
    stamina_only = ActionCostModifier(
        source="Stamina only",
        operation=CostModifierOperation.FLAT_REDUCTION,
        value=100,
        resources=(ResourceType.STAMINA,),
    )

    result = ActionCostModifierSet((first, second, stamina_only)).applicable_to(_cost())

    assert result == (first, second)


def test_invalid_modifier_contracts_are_rejected():
    with pytest.raises(ValueError):
        ActionCostModifier(
            source="",
            operation=CostModifierOperation.FLAT_REDUCTION,
            value=1,
            resources=(ResourceType.MAGICKA,),
        )

    with pytest.raises(ValueError):
        ActionCostModifier(
            source="Bad percent",
            operation=CostModifierOperation.PERCENT_REDUCTION,
            value=7,
            resources=(ResourceType.MAGICKA,),
        )

    with pytest.raises(ValueError):
        ActionCostModifier(
            source="No resource",
            operation=CostModifierOperation.FLAT_REDUCTION,
            value=1,
            resources=(),
        )
