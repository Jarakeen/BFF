from __future__ import annotations

import sqlite3

import pytest

from minmax.character_build.character_class import CharacterClass
from services.class_mastery_classification_service import ClassMasteryBoundary
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT,
                class_type TEXT,
                skill_line TEXT,
                description TEXT,
                is_passive INTEGER
            )
            """
        )
        rows = [
            (1, 1001, "Above and Beyond", "Nightblade", "Class Mastery", "critical", 1),
            (2, 1002, "An Eye for Exploitation", "Nightblade", "Class Mastery", "power", 1),
            (3, 1003, "Bright Harbinger", "Templar", "Class Mastery", "power", 1),
            (4, 1004, "Font of Power", "Sorcerer", "Class Mastery", "power", 1),
            (5, 1005, "Calculated Defense", "Sorcerer", "Class Mastery", "power", 1),
            (6, 1006, "Sphere of Influence", "Sorcerer", "Class Mastery", "recovery", 1),
            (7, 1007, "Nothing Wasted", "Necromancer", "Class Mastery", "health and power", 1),
            (8, 1008, "Wild Adaptation", "Warden", "Class Mastery", "power", 1),
            (9, 1009, "Glacial Obstinance", "Warden", "Class Mastery", "power", 1),
        ]
        db.executemany(
            "INSERT INTO skill VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        db.commit()
    return path


def test_nightblade_critical_damage_selects_reviewed_standing_mastery(tmp_path):
    service = ExtremeClassMasteryPairService(_database(tmp_path))

    best = service.best_for_class(
        CharacterClass.NIGHTBLADE,
        "critical_damage",
        reference_value=0.50,
    )

    assert best is not None
    assert best.passive_names == ("Above and Beyond",)
    assert best.additive_ratio == pytest.approx(0.25)
    assert best.projected_delta == pytest.approx(0.25)
    assert best.boundary is ClassMasteryBoundary.STANDING_SELF_CONTAINED


def test_templar_flat_power_mastery_scores_without_reference_value(tmp_path):
    service = ExtremeClassMasteryPairService(_database(tmp_path))

    best = service.best_for_class(CharacterClass.TEMPLAR, "spell_damage")

    assert best is not None
    assert best.passive_names == ("Bright Harbinger",)
    assert best.flat == pytest.approx(600.0)
    assert best.projected_delta == pytest.approx(600.0)
    assert best.boundary is ClassMasteryBoundary.COMBAT_STATE_DEPENDENT


def test_sorcerer_combines_two_legal_masteries_and_needs_reference_for_percent_math(tmp_path):
    service = ExtremeClassMasteryPairService(_database(tmp_path))

    assert service.best_for_class(
        CharacterClass.SORCERER,
        "spell_damage",
        higher_max_resource=35000,
    ) is None

    best = service.best_for_class(
        CharacterClass.SORCERER,
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    assert best is not None
    assert set(best.passive_names) == {"Font of Power", "Calculated Defense"}
    assert best.percent == pytest.approx(0.32)
    assert best.projected_delta == pytest.approx(1600.0)
    assert best.boundary is ClassMasteryBoundary.COMBAT_STATE_DEPENDENT
    assert len(best.passive_names) == 2


def test_pair_search_never_selects_more_than_two_masteries(tmp_path):
    service = ExtremeClassMasteryPairService(_database(tmp_path))

    rows = service.candidates_for_class(
        CharacterClass.SORCERER,
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
        include_empty=True,
    )

    assert rows
    assert max(len(row.passive_names) for row in rows) <= 2
    assert any(not row.passive_names for row in rows)


def test_worst_runtime_boundary_is_retained_when_pair_combines_conditions(tmp_path):
    service = ExtremeClassMasteryPairService(_database(tmp_path))

    rows = service.candidates_for_class(
        CharacterClass.WARDEN,
        "spell_damage",
        reference_value=5000,
    )
    pair = next(row for row in rows if len(row.passive_names) == 2)

    assert set(pair.passive_names) == {"Wild Adaptation", "Glacial Obstinance"}
    assert pair.boundary is ClassMasteryBoundary.TARGET_STATE_DEPENDENT
    assert len(pair.conditions) == 2


def test_best_pure_class_routes_only_reports_classes_with_reviewed_scoring(tmp_path):
    service = ExtremeClassMasteryPairService(_database(tmp_path))

    rows = service.best_pure_class_routes(
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    assert rows
    assert rows[0].projected_delta >= rows[-1].projected_delta
    classes = {row.base_class for row in rows}
    assert CharacterClass.SORCERER in classes
    assert CharacterClass.TEMPLAR in classes
    assert CharacterClass.ARCANIST not in classes
