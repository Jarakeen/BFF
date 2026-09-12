from __future__ import annotations

import sqlite3

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)


class _Repository:
    def __init__(self, database_path, rows, descriptions):
        self.database_path = str(database_path)
        self._rows = tuple(rows)
        self._descriptions = dict(descriptions)

    def list_names(self):
        return self._rows

    def description(self, name):
        return self._descriptions.get(name)

    def resolve(self, name):
        if name == "Strong Meal":
            return [
                Effect(
                    source="test",
                    stat=StatId.MAX_MAGICKA,
                    operation=EffectOperation.ADD,
                    value=5000.0,
                    unit=EffectUnit.FLAT,
                )
            ], []
        if name == "Strong Drink":
            return [
                Effect(
                    source="test",
                    stat=StatId.MAX_MAGICKA,
                    operation=EffectOperation.ADD,
                    value=4200.0,
                    unit=EffectUnit.FLAT,
                )
            ], []
        return [], [f"Food/Drink has no mapped static character-sheet stats: {name}"]


def _database(tmp_path, names):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE entity (id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, name TEXT NOT NULL)"
        )
        for index, (kind, name) in enumerate(names, start=1):
            connection.execute(
                "INSERT INTO entity(id, entity_type, name) VALUES (?, ?, ?)",
                (str(index), kind, name),
            )
    return path


def test_xp_flavor_and_recovery_only_unmapped_items_are_proven_irrelevant(tmp_path):
    typed = (
        ("food", "Strong Meal"),
        ("drink", "Strong Drink"),
        ("drink", "Experience Drink"),
        ("drink", "Recovery Lager"),
        ("food", "Potato Crime"),
    )
    repository = _Repository(
        _database(tmp_path, typed),
        tuple(name for _kind, name in typed),
        {
            "Experience Drink": "You gain a 100% Experience Point bonus for 30 minutes.",
            "Recovery Lager": "Increase Magicka and Stamina Recovery by AB_DERIVED_VALUE for 1 hour.",
            "Potato Crime": "Mushy, foul-smelling, and lukewarm to the touch.",
        },
    )

    result = ExtremeResourceProvisioningProjectionService(repository).build("max_magicka")

    assert result.projection_complete is True
    assert result.food_witness == "Strong Meal"
    assert result.drink_witness == "Strong Drink"
    assert result.unresolved == ()


def test_unmapped_tooltip_that_may_change_max_resource_stays_a_blocker(tmp_path):
    typed = (
        ("food", "Strong Meal"),
        ("drink", "Strong Drink"),
        ("food", "Mystery Max Meal"),
    )
    repository = _Repository(
        _database(tmp_path, typed),
        tuple(name for _kind, name in typed),
        {"Mystery Max Meal": "Increase Max Magicka by AB_DERIVED_VALUE for 2 hours."},
    )

    result = ExtremeResourceProvisioningProjectionService(repository).build("max_magicka")

    assert result.projection_complete is False
    assert any("Mystery Max Meal" in row for row in result.unresolved)
