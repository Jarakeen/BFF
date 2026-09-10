from __future__ import annotations

import sqlite3

from services.rotation_healer_esologs_canonical_skill_alias_service import (
    RotationHealerEsoLogsCanonicalSkillAliasService,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE ability (ability_id INTEGER, index_name TEXT)"
        )
        connection.executemany(
            "INSERT INTO ability (ability_id, index_name) VALUES (?, ?)",
            (
                (85840, "Budding Seeds"),
                (40079, "Radiating Regeneration"),
                (40058, "Illustrious Healing"),
                (42038, "Energy Orb"),
                (61505, "Echoing Vigor"),
                (99901, "Nature's Grasp"),
            ),
        )
    return path


def test_resolves_display_index_name_from_canonical_snake_case(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    resolved = service.resolve("budding_seeds")

    assert resolved is not None
    assert resolved.canonical_skill_id == "budding_seeds"
    assert resolved.ability_game_ids == (85840,)


def test_normalizes_requested_display_name_too(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    resolved = service.resolve("Radiating Regeneration")

    assert resolved is not None
    assert resolved.canonical_skill_id == "radiating_regeneration"
    assert resolved.ability_game_ids == (40079,)


def test_normalizes_apostrophes_and_punctuation(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    resolved = service.resolve("natures_grasp")

    assert resolved is not None
    assert resolved.canonical_skill_id == "natures_grasp"
    assert resolved.ability_game_ids == (99901,)


def test_does_not_resolve_unrelated_skill(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    assert service.resolve("combat_prayer") is None
