from __future__ import annotations

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_consumable_result_support import (
    extreme_food_winners,
    format_extreme_food_result,
)


class FakeProvisioningRepository:
    def __init__(self, rows):
        self.rows = rows

    @staticmethod
    def canonical_name(name: str) -> str:
        return str(name or "").strip()

    def list_names(self):
        return tuple(self.rows)

    def resolve(self, name: str):
        stats = self.rows[name]
        effects = [
            Effect(
                source=f"Food/Drink: {name}",
                stat=stat,
                operation=EffectOperation.ADD,
                value=value,
                unit=EffectUnit.FLAT,
            )
            for stat, value in stats.items()
        ]
        return effects, []


def test_resource_food_winners_preserve_all_equal_maximum_recipes():
    repository = FakeProvisioningRepository(
        {
            "Firsthold Fruit and Cheese Plate": {StatId.MAX_MAGICKA: 6048.0},
            "Thrice-Baked Gorapple Pie": {StatId.MAX_MAGICKA: 6048.0},
            "Tomato Garlic Chutney": {StatId.MAX_MAGICKA: 6048.0},
            "Lesser Magicka Food": {StatId.MAX_MAGICKA: 5000.0},
        }
    )

    result = extreme_food_winners(
        "max_magicka",
        selected_food="Tomato Garlic Chutney",
        repository=repository,
    )

    assert result.value == 6048.0
    assert result.representative == "Tomato Garlic Chutney"
    assert result.selected_is_winner is True
    assert result.winners == (
        "Firsthold Fruit and Cheese Plate",
        "Thrice-Baked Gorapple Pie",
        "Tomato Garlic Chutney",
    )
    primary, detail = format_extreme_food_result(result)
    assert primary == "Tomato Garlic Chutney • 3-way tie"
    assert "Firsthold Fruit and Cheese Plate" in detail
    assert "Thrice-Baked Gorapple Pie" in detail


def test_missing_maximum_food_is_reported_instead_of_silently_showing_blank():
    repository = FakeProvisioningRepository(
        {
            "Garlic-and-Pepper Venison Steak": {StatId.MAX_HEALTH: 6608.0},
            "Lilmoth Garlic Hagfish": {StatId.MAX_HEALTH: 6608.0},
        }
    )

    result = extreme_food_winners(
        "max_health",
        selected_food="",
        repository=repository,
    )

    primary, detail = format_extreme_food_result(result)
    assert primary.startswith("MAX FOOD NOT APPLIED • use ")
    assert "6608" in primary
    assert detail == "Garlic-and-Pepper Venison Steak, Lilmoth Garlic Hagfish"


def test_non_food_sheet_objective_does_not_invent_an_arbitrary_recipe():
    repository = FakeProvisioningRepository(
        {
            "Health Food": {StatId.MAX_HEALTH: 6608.0},
            "Magicka Food": {StatId.MAX_MAGICKA: 6048.0},
        }
    )

    result = extreme_food_winners(
        "weapon_damage",
        selected_food="",
        repository=repository,
    )

    assert result.relevant is False
    assert format_extreme_food_result(result) == (
        "No food improves this exact objective",
        None,
    )
