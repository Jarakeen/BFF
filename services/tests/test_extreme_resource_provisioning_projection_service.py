from __future__ import annotations

import sqlite3

import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)


class _Repository:
    def __init__(self, database_path, rows, effects):
        self.database_path = str(database_path)
        self._rows = tuple(rows)
        self._effects = dict(effects)

    def list_names(self):
        return self._rows

    def resolve(self, name):
        return list(self._effects.get(name, ())), []


def _effect(name: str, stat: StatId, value: float) -> Effect:
    return Effect(
        source=f"Food/Drink: {name}",
        stat=stat,
        operation=EffectOperation.ADD,
        value=value,
        unit=EffectUnit.FLAT,
    )


def _database(tmp_path, typed_names):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE entity (id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, name TEXT NOT NULL)"
        )
        for index, (kind, name) in enumerate(typed_names, start=1):
            connection.execute(
                "INSERT INTO entity(id, entity_type, name) VALUES (?, ?, ?)",
                (str(index), kind, name),
            )
    return path


def test_magicka_projection_keeps_strongest_food_and_weaker_drink_for_bright_throat(tmp_path):
    rows = (
        ("food", "Huge Magicka Meal"),
        ("food", "Small Magicka Meal"),
        ("drink", "Best Magicka Drink"),
        ("drink", "Small Magicka Drink"),
    )
    path = _database(tmp_path, rows)
    repository = _Repository(
        path,
        tuple(name for _kind, name in rows),
        {
            "Huge Magicka Meal": (_effect("Huge Magicka Meal", StatId.MAX_MAGICKA, 5000),),
            "Small Magicka Meal": (_effect("Small Magicka Meal", StatId.MAX_MAGICKA, 3000),),
            "Best Magicka Drink": (_effect("Best Magicka Drink", StatId.MAX_MAGICKA, 4200),),
            "Small Magicka Drink": (_effect("Small Magicka Drink", StatId.MAX_MAGICKA, 2000),),
        },
    )

    result = ExtremeResourceProvisioningProjectionService(repository).build("max_magicka")

    assert result.projection_complete is True
    assert result.foods_reviewed == 4
    assert result.food_witness == "Huge Magicka Meal"
    assert result.drink_witness == "Best Magicka Drink"
    assert result.choices == ("Huge Magicka Meal", "Best Magicka Drink")


def test_stamina_projection_keeps_strongest_food_and_weaker_drink_for_bone_pirate(tmp_path):
    rows = (
        ("food", "Huge Stamina Meal"),
        ("drink", "Best Stamina Drink"),
    )
    path = _database(tmp_path, rows)
    repository = _Repository(
        path,
        tuple(name for _kind, name in rows),
        {
            "Huge Stamina Meal": (_effect("Huge Stamina Meal", StatId.MAX_STAMINA, 5000),),
            "Best Stamina Drink": (_effect("Best Stamina Drink", StatId.MAX_STAMINA, 3900),),
        },
    )

    result = ExtremeResourceProvisioningProjectionService(repository).build("max_stamina")

    assert result.projection_complete is True
    assert result.food_witness == "Huge Stamina Meal"
    assert result.drink_witness == "Best Stamina Drink"
    assert result.choices == ("Huge Stamina Meal", "Best Stamina Drink")


def test_projection_fails_closed_when_food_drink_identity_is_not_proven(tmp_path):
    rows = (("provisioning", "Mystery Provisioning"),)
    path = _database(tmp_path, rows)
    repository = _Repository(
        path,
        ("Mystery Provisioning",),
        {"Mystery Provisioning": (_effect("Mystery Provisioning", StatId.MAX_MAGICKA, 6000),)},
    )

    result = ExtremeResourceProvisioningProjectionService(repository).build("max_magicka")

    assert result.projection_complete is False
    assert any("no canonical food/drink identity" in row for row in result.unresolved)


@pytest.mark.parametrize("objective", ("max_health", "spell_damage"))
def test_projection_rejects_unreviewed_objectives(tmp_path, objective):
    path = _database(tmp_path, (("food", "Meal"),))
    repository = _Repository(path, ("Meal",), {})

    with pytest.raises(KeyError):
        ExtremeResourceProvisioningProjectionService(repository).build(objective)
