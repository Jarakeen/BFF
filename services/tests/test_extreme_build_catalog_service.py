from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_build.character_class import CharacterClass
from services import extreme_build_catalog_service as module
from services.extreme_build_catalog_service import ExtremeBuildCatalogService


def test_three_line_set_has_exactly_28_six_slot_allocations():
    rows = ExtremeBuildCatalogService._six_slot_allocations(
        ("assassination", "storm_calling", "winters_embrace")
    )

    assert len(rows) == 28
    assert len(set(rows)) == 28
    assert all(sum(count for _, count in row) == 6 for row in rows)


def test_passive_formula_reuses_reviewed_slot_math():
    formula = ExtremeBuildCatalogService._passive_formula(
        ("daedric_summoning", "storm_calling", "winters_embrace"),
        {"daedric_summoning": 0, "storm_calling": 0, "winters_embrace": 6},
        "physical_resistance",
    )

    assert formula is not None
    assert formula.flat == pytest.approx(7440.0)
    assert formula.percent_of_reference == 0.0
    assert formula.sources == ("Frozen Armor (6 Winter's Embrace slots)",)


def test_catalog_keeps_explanations_in_python_not_generated_json(monkeypatch, tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"catalog-test")

    config = SimpleNamespace(
        base_class=CharacterClass.SORCERER,
        equipped_skill_lines=("daedric_summoning", "storm_calling", "winters_embrace"),
        is_pure_class=False,
        class_mastery_available=False,
        foreign_skill_lines=("winters_embrace",),
    )
    monkeypatch.setattr(module.ExtremeClassConfigurationService, "all_candidates", lambda: (config,))
    monkeypatch.setattr(module, "load_skill_choices", lambda _database: [])

    catalog = ExtremeBuildCatalogService(database).build()

    for section in (
        "metadata",
        "class_configurations",
        "bar_allocations",
        "skill_families",
        "passive_allocation_formulas",
        "dynamic_runtime_inputs",
    ):
        assert "_why" not in catalog[section]

    key = "daedric_summoning|storm_calling|winters_embrace"
    assert len(catalog["bar_allocations"]["by_line_set"][key]) == 28
    assert catalog["metadata"]["source_database_sha256"] == (
        ExtremeBuildCatalogService(database).database_fingerprint()
    )


def test_skill_family_catalog_preserves_morph_alternatives_and_standing_descriptors(monkeypatch, tmp_path):
    database = tmp_path / "eso.db"
    database.write_bytes(b"skill-family-test")

    rows = [
        {
            "ability_id": 1001,
            "base_ability_id": 1000,
            "name": "Tome-Bearer's Inspiration",
            "skill_line": "Herald of the Tome",
            "morph": 1,
        },
        {
            "ability_id": 1002,
            "base_ability_id": 1000,
            "name": "Inspired Scholarship",
            "skill_line": "Herald of the Tome",
            "morph": 2,
        },
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _database: rows)
    monkeypatch.setattr(module, "is_player_active", lambda row: True)
    monkeypatch.setattr(module, "is_ultimate", lambda row: False)

    families = ExtremeBuildCatalogService(database)._skill_family_catalog()
    herald = families["herald_of_the_tome"]

    assert len(herald) == 1
    alternatives = herald[0]["alternatives"]
    assert {item["name"] for item in alternatives} == {
        "Tome-Bearer's Inspiration",
        "Inspired Scholarship",
    }
    assert all(item["standing_effects"] for item in alternatives)
    assert any(
        effect["stacking_key"] == "major_sorcery"
        and effect["reference_sensitive"] is True
        for item in alternatives
        for effect in item["standing_effects"]
    )
