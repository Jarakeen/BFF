import pytest

from minmax.resource_costs import (
    BaseActionCost,
    ResourceType,
    decode_resource_mechanic,
    resolve_base_action_cost,
)


def test_decode_single_resource_mechanics():
    assert decode_resource_mechanic(1) == (ResourceType.MAGICKA,)
    assert decode_resource_mechanic(4) == (ResourceType.STAMINA,)
    assert decode_resource_mechanic(8) == (ResourceType.ULTIMATE,)
    assert decode_resource_mechanic(32) == (ResourceType.HEALTH,)


def test_decode_compound_resource_mechanics():
    assert decode_resource_mechanic(5) == (
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
    )
    assert decode_resource_mechanic(36) == (
        ResourceType.STAMINA,
        ResourceType.HEALTH,
    )


def test_decode_resource_mechanic_rejects_unknown_bits():
    with pytest.raises(ValueError, match="unknown_bits"):
        decode_resource_mechanic(2)


def test_decode_resource_mechanic_rejects_zero():
    with pytest.raises(ValueError, match="Unsupported resource mechanic"):
        decode_resource_mechanic(0)


def test_resolve_base_action_cost_uses_ranked_ability_row_values():
    cost = resolve_base_action_cost(
        ability_id=40103503,
        base_cost=3780,
        base_mechanic=1,
        rank=4,
        morph=0,
    )

    assert cost == BaseActionCost(
        amount=3780.0,
        resources=(ResourceType.MAGICKA,),
        ability_id=40103503,
        rank=4,
        morph=0,
        base_mechanic=1,
    )


def test_resolve_base_action_cost_preserves_compound_cost():
    cost = resolve_base_action_cost(
        ability_id=23819,
        base_cost=1148,
        base_mechanic=5,
        rank=4,
        morph=1,
    )

    assert cost.amount == 1148.0
    assert cost.resources == (
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
    )


def test_resolve_base_action_cost_rejects_non_positive_cost():
    with pytest.raises(ValueError, match="positive base cost"):
        resolve_base_action_cost(
            ability_id=217699,
            base_cost=0,
            base_mechanic=5,
            rank=1,
            morph=0,
        )
