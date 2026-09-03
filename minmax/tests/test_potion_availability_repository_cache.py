from __future__ import annotations

import json
import sqlite3

from minmax.potion_availability_repository import PotionAvailabilityRepository


def _write_fixture(database, processed) -> None:
    processed.write_text(
        json.dumps(
            {
                "effects": [
                    {
                        "effect_name": "Restore Magicka",
                        "source_files": ["fixture.html"],
                        "formulas": [
                            {
                                "ingredients": ["Corn Flower", "Lady's Smock", "Namira's Rot"],
                                "effects": [
                                    "Restore Magicka",
                                    "Increase Spell Power",
                                    "Spell Critical",
                                ],
                            }
                        ],
                    },
                    {
                        "effect_name": "Increase Spell Power",
                        "source_files": ["fixture.html"],
                        "formulas": [
                            {
                                "ingredients": ["Corn Flower", "Lady's Smock", "Namira's Rot"],
                                "effects": [
                                    "Restore Magicka",
                                    "Increase Spell Power",
                                    "Spell Critical",
                                ],
                            }
                        ],
                    },
                    {
                        "effect_name": "Spell Critical",
                        "source_files": ["fixture.html"],
                        "formulas": [
                            {
                                "ingredients": ["Corn Flower", "Lady's Smock", "Namira's Rot"],
                                "effects": [
                                    "Restore Magicka",
                                    "Increase Spell Power",
                                    "Spell Critical",
                                ],
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    with sqlite3.connect(database) as db:
        db.executescript(
            """
            CREATE TABLE effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT
            );
            CREATE TABLE effect_variant (
                id INTEGER PRIMARY KEY,
                effect_id INTEGER NOT NULL,
                type TEXT,
                raw_json TEXT
            );
            INSERT INTO effect VALUES
                (1, 'Restore Magicka', 'alchemy'),
                (2, 'Increase Spell Power', 'alchemy'),
                (3, 'Spell Critical', 'alchemy');
            INSERT INTO effect_variant VALUES
                (101, 1, 'Potion', NULL),
                (102, 2, 'Potion', NULL),
                (103, 3, 'Potion', NULL);
            """
        )


class _CountingPotionRepository(PotionAvailabilityRepository):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.catalog_builds = 0
        self.effect_reads = 0

    def _database_catalog_payload(self):
        self.catalog_builds += 1
        return super()._database_catalog_payload()

    def _effect_variants(self, traits, selected_label):
        self.effect_reads += 1
        return super()._effect_variants(traits, selected_label)


def test_resolution_cache_reuses_same_normalized_selection(tmp_path) -> None:
    database = tmp_path / "eso.db"
    processed = tmp_path / "alchemy_effects.json"
    _write_fixture(database, processed)
    repository = _CountingPotionRepository(database, processed)

    first = repository.resolve("spell power")
    second = repository.resolve("  SPELL   POWER  ")

    assert first == second
    assert repository.effect_reads == 1


def test_catalog_cache_reuses_parsed_processed_payload(tmp_path) -> None:
    database = tmp_path / "eso.db"
    processed = tmp_path / "alchemy_effects.json"
    _write_fixture(database, processed)
    repository = PotionAvailabilityRepository(database, processed)

    first = repository._catalog()
    processed.write_text("{}", encoding="utf-8")
    second = repository._catalog()

    assert first is second
    assert first.formulas
