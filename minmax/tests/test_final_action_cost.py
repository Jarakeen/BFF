from __future__ import annotations

import pytest

from minmax.final_action_cost import calculate_final_action_cost
from minmax.resource_cost_modifiers import (
    ActionCostModifier,
    ActionCostModifierSet,
    CostModifierOperation,
)
from minmax.resource_costs import ResourceType, resolve_base_action_cost


def _modifier(
    source: str,
    operation: CostModifierOperation,
    value: float,
    *resources: ResourceType,
) -> ActionCostModifier:
    return ActionCostModifier(
        source=source,
        operation=operation,
        value=value,
        resources=tuple(resources),
    )


@pytest.mark.parametrize(
    ("ability_id", "base_cost", "observed"),
    [
        (93807, 2430, 1826),   # Budding Seeds
        (43447, 3780, 2933),   # Energy Orb
        (41189, 4590, 3597),   # Combat Prayer
        (41255, 3510, 2712),   # Illustrious Healing
        (43363, 1620, 1162),   # Inner Fire
    ],
)
def test_live_observed_magicka_costs_match_verified_reduction_formula(
    ability_id: int,
    base_cost: int,
    observed: int,
) -> None:
    base = resolve_base_action_cost(
        ability_id=ability_id,
        base_cost=base_cost,
        base_mechanic=1,
        rank=4,
    )
    modifiers = ActionCostModifierSet(
        (
            _modifier(
                "Observed flat spell-cost reduction",
                CostModifierOperation.FLAT_REDUCTION,
                203,
                ResourceType.MAGICKA,
            ),
            _modifier(
                "Observed total percentage Magicka-cost reduction",
                CostModifierOperation.PERCENT_REDUCTION,
                0.18,
                ResourceType.MAGICKA,
            ),
        )
    )

    final = calculate_final_action_cost(base, modifiers)

    assert final.for_resource(ResourceType.MAGICKA).final_amount == observed


def test_rounding_is_nearest_half_up_not_floor() -> None:
    base = resolve_base_action_cost(
        ability_id=41255,
        base_cost=3510,
        base_mechanic=1,
        rank=4,
        morph=1,
    )
    modifiers = ActionCostModifierSet(
        (
            _modifier(
                "flat",
                CostModifierOperation.FLAT_REDUCTION,
                203,
                ResourceType.MAGICKA,
            ),
            _modifier(
                "percent",
                CostModifierOperation.PERCENT_REDUCTION,
                0.18,
                ResourceType.MAGICKA,
            ),
        )
    )

    resource_cost = calculate_final_action_cost(base, modifiers).for_resource(
        ResourceType.MAGICKA
    )

    assert resource_cost.raw_amount == pytest.approx(2711.74)
    assert resource_cost.final_amount == 2712


def test_compound_cost_applies_resource_specific_reductions_independently() -> None:
    molten_whip = resolve_base_action_cost(
        ability_id=23819,
        base_cost=1148,
        base_mechanic=5,
        rank=4,
        morph=1,
    )
    modifiers = ActionCostModifierSet(
        (
            _modifier(
                "Magicka-only flat reduction",
                CostModifierOperation.FLAT_REDUCTION,
                100,
                ResourceType.MAGICKA,
            ),
            _modifier(
                "Stamina-only percent reduction",
                CostModifierOperation.PERCENT_REDUCTION,
                0.10,
                ResourceType.STAMINA,
            ),
        )
    )

    final = calculate_final_action_cost(molten_whip, modifiers)

    assert final.for_resource(ResourceType.MAGICKA).final_amount == 1048
    assert final.for_resource(ResourceType.STAMINA).final_amount == 1033


def test_percentage_increase_remains_explicitly_unverified() -> None:
    base = resolve_base_action_cost(
        ability_id=1,
        base_cost=1000,
        base_mechanic=1,
    )
    modifiers = ActionCostModifierSet(
        (
            _modifier(
                "Unverified cost increase",
                CostModifierOperation.PERCENT_INCREASE,
                0.25,
                ResourceType.MAGICKA,
            ),
        )
    )

    with pytest.raises(ValueError, match="not yet verified"):
        calculate_final_action_cost(base, modifiers)


def test_combined_percentage_reduction_over_100_percent_is_rejected() -> None:
    base = resolve_base_action_cost(
        ability_id=1,
        base_cost=1000,
        base_mechanic=1,
    )
    modifiers = ActionCostModifierSet(
        (
            _modifier(
                "A",
                CostModifierOperation.PERCENT_REDUCTION,
                0.60,
                ResourceType.MAGICKA,
            ),
            _modifier(
                "B",
                CostModifierOperation.PERCENT_REDUCTION,
                0.50,
                ResourceType.MAGICKA,
            ),
        )
    )

    with pytest.raises(ValueError, match="exceeds 100%"):
        calculate_final_action_cost(base, modifiers)
