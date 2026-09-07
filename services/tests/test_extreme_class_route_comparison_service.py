from __future__ import annotations

import sqlite3

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_route_comparison_service import (
    ExtremeClassRouteComparisonService,
    ExtremeClassRouteKind,
)
from services.extreme_subclass_skill_bar_service import (
    ExtremeSubclassBarSkill,
    ExtremeSubclassSkillBarResult,
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


class _MaterializingBarService:
    def materialize(self, slot_counts, *, objective_key=""):
        if not slot_counts or sum(count for _, count in slot_counts) != 6:
            return None
        lines = [line for line, count in slot_counts for _ in range(count)]
        skills = []
        for index, line in enumerate(lines):
            name = f"{line} skill {index + 1}"
            if objective_key in {"spell_critical", "weapon_critical"} and line == "assassination" and index == 0:
                name = "Relentless Focus"
            skills.append(
                ExtremeSubclassBarSkill(
                    ability_id=10000 + index,
                    base_ability_id=20000 + index,
                    name=name,
                    skill_line_id=line,
                    is_ultimate=index == 5,
                    morph=1,
                )
            )
        return ExtremeSubclassSkillBarResult(
            slot_counts=slot_counts,
            skills=tuple(skills),
        )


class _RejectingBarService:
    def materialize(self, slot_counts, *, objective_key=""):
        return None


def _service(tmp_path, *, reject_bars: bool = False):
    bars = _RejectingBarService() if reject_bars else _MaterializingBarService()
    return ExtremeClassRouteComparisonService(
        _database(tmp_path),
        skill_bar_service=bars,
    )


def test_route_comparison_keeps_subclasses_unresolved_even_with_reviewed_lower_bounds(tmp_path):
    service = _service(tmp_path)

    result = service.compare(
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    subclasses = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.SUBCLASS]
    assert subclasses
    assert result.unresolved_subclass_count == len(subclasses)
    assert any(row.projected_delta is not None for row in subclasses)
    assert any(row.projected_delta is None for row in subclasses)
    assert result.reviewed_subclass_lower_bound_count > 0
    assert result.can_declare_global_winner is False


def test_spell_damage_subclass_lower_bound_uses_materialized_legal_bar(tmp_path):
    service = _service(tmp_path)

    result = service.compare(
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    best = result.best_reviewed_subclass_lower_bound
    assert best is not None
    assert best.route_kind is ExtremeClassRouteKind.SUBCLASS
    assert best.projected_delta == 648.0
    assert "storm_calling" in best.equipped_skill_lines
    assert best.score_status == "reviewed_subclass_materialized_lower_bound"
    assert sum(count for _, count in best.slot_counts) == 6
    assert best.reviewed_sources == ("Expert Mage (6 Sorcerer slots)",)
    assert len(best.skill_bar_names) == 6
    assert len(best.skill_bar_ability_ids) == 6
    assert result.can_declare_global_winner is False


def test_reviewed_while_slotted_skill_adds_to_subclass_critical_lower_bound(tmp_path):
    service = _service(tmp_path)

    result = service.compare("spell_critical")
    best = result.best_reviewed_subclass_lower_bound

    assert best is not None
    assert "assassination" in best.equipped_skill_lines
    assert "Relentless Focus" in best.skill_bar_names
    assert any("Pressure Points" in source for source in best.reviewed_sources)
    assert any("Relentless Focus" in source for source in best.reviewed_sources)
    assert best.projected_delta > 0


def test_unmaterializable_allocation_is_not_reported_as_numeric_lower_bound(tmp_path):
    service = _service(tmp_path, reject_bars=True)

    result = service.compare(
        "spell_damage",
        reference_value=5000,
        higher_max_resource=35000,
    )

    subclasses = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.SUBCLASS]
    assert result.reviewed_subclass_lower_bound_count == 0
    assert result.best_reviewed_subclass_lower_bound is None
    assert any(row.score_status == "pending_canonical_bar_materialization" for row in subclasses)
    assert all(row.projected_delta is None for row in subclasses)


def test_best_reviewed_pure_route_is_not_mislabeled_global_winner(tmp_path):
    service = _service(tmp_path)

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
    service = _service(tmp_path)

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
    service = _service(tmp_path)

    result = service.compare("spell_damage", reference_value=5000, higher_max_resource=35000)
    subclasses = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.SUBCLASS]

    assert subclasses
    assert all(row.mastery_names == () for row in subclasses)


def test_percent_subclass_line_requires_reference_value_before_it_gets_lower_bound(tmp_path):
    service = _service(tmp_path)

    without_reference = service.compare("magicka_recovery")
    with_reference = service.compare("magicka_recovery", reference_value=1000)

    assert without_reference.reviewed_subclass_lower_bound_count == 0
    assert with_reference.reviewed_subclass_lower_bound_count > 0
    assert with_reference.best_reviewed_subclass_lower_bound is not None
    assert with_reference.best_reviewed_subclass_lower_bound.projected_delta == 200.0
