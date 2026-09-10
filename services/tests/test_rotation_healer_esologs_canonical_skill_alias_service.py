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


def test_reviewed_periodic_effect_aliases_are_component_specific(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    seeds = service.reviewed_periodic_effects(
        "Budding Seeds",
        coefficient_number=2,
        game_version="U50",
    )
    illustrious = service.reviewed_periodic_effects(
        "illustrious_healing",
        coefficient_number=1,
        game_version="u50",
    )

    assert seeds is not None
    assert seeds.canonical_skill_id == "budding_seeds"
    assert seeds.coefficient_number == 2
    assert seeds.ability_game_ids == (129434,)
    assert seeds.game_version == "U50"
    assert any("50/50" in item for item in seeds.evidence)
    assert any("85841 remains unpromoted" in item for item in seeds.evidence)

    assert illustrious is not None
    assert illustrious.ability_game_ids == (40059,)
    assert any("79/79" in item for item in illustrious.evidence)


def test_reviewed_periodic_effect_aliases_cover_all_cross_fight_promotions(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    expected = {
        ("budding_seeds", 2): (129434,),
        ("radiating_regeneration", 1): (40079,),
        ("illustrious_healing", 1): (40059,),
        ("energy_orb", 1): (42039,),
        ("echoing_vigor", 1): (61506,),
    }

    resolved = {
        key: service.reviewed_periodic_effects(
            key[0],
            coefficient_number=key[1],
            game_version="U50",
        )
        for key in expected
    }

    assert {
        key: value.ability_game_ids if value is not None else None
        for key, value in resolved.items()
    } == expected


def test_reviewed_periodic_effect_aliases_fail_closed_for_other_component_or_version(tmp_path):
    service = RotationHealerEsoLogsCanonicalSkillAliasService(_database(tmp_path))

    assert service.reviewed_periodic_effects(
        "budding_seeds",
        coefficient_number=1,
        game_version="U50",
    ) is None
    assert service.reviewed_periodic_effects(
        "budding_seeds",
        coefficient_number=2,
        game_version="U49",
    ) is None
