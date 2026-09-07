from __future__ import annotations

import sqlite3

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_route_comparison_service import (
    ExtremeClassRouteComparisonService,
    ExtremeClassRouteKind,
)


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
        db.executemany(
            "INSERT INTO skill VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1001, "Above and Beyond", "Nightblade", "Class Mastery", "critical", 1),
                (2, 1002, "Bright Harbinger", "Templar", "Class Mastery", "power", 1),
                (3, 1003, "Font of Power", "Sorcerer", "Class Mastery", "power", 1),
                (4, 1004, "Calculated Defense", "Sorcerer", "Class Mastery", "power", 1),
            ],
        )
        db.commit()
    return path


def test_route_comparison_keeps_subclasses_explicitly_unscored(tmp_path):
    service = ExtremeClassRouteComparisonService(_database(tmp_path))

    result = service.compare(
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    subclasses = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.SUBCLASS]
    assert subclasses
    assert result.unresolved_subclass_count == len(subclasses)
    assert all(row.projected_delta is None for row in subclasses)
    assert all(row.score_status == "pending_subclass_effect_resolution" for row in subclasses)
    assert result.can_declare_global_winner is False


def test_best_reviewed_pure_route_is_not_mislabeled_global_winner(tmp_path):
    service = ExtremeClassRouteComparisonService(_database(tmp_path))

    result = service.compare(
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    best = result.best_reviewed_pure_route
    assert best is not None
    assert best.route_kind is ExtremeClassRouteKind.PURE_MASTERY
    assert best.base_class is CharacterClass.SORCERER
    assert set(best.mastery_names) == {"Font of Power", "Calculated Defense"}
    assert best.projected_delta == 1600.0
    assert result.can_declare_global_winner is False


def test_pure_route_uses_native_three_line_configuration(tmp_path):
    service = ExtremeClassRouteComparisonService(_database(tmp_path))

    result = service.compare("critical_damage", reference_value=0.5)
    nightblade = next(
        row
        for row in result.routes
        if row.route_kind is ExtremeClassRouteKind.PURE_MASTERY
        and row.base_class is CharacterClass.NIGHTBLADE
    )

    assert set(nightblade.equipped_skill_lines) == {"assassination", "shadow", "siphoning"}
    assert nightblade.mastery_names == ("Above and Beyond",)


def test_subclass_routes_never_claim_class_mastery(tmp_path):
    service = ExtremeClassRouteComparisonService(_database(tmp_path))

    result = service.compare("spell_damage", reference_value=5000, higher_max_resource=35000)
    subclasses = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.SUBCLASS]

    assert subclasses
    assert all(row.mastery_names == () for row in subclasses)
