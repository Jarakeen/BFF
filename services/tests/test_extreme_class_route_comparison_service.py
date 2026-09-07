from __future__ import annotations

import sqlite3

import pytest

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_route_comparison_service import (
    ExtremeClassRouteComparisonService,
    ExtremeClassRouteKind,
)
from services.extreme_subclass_skill_bar_service import (
    ExtremeSubclassBarSkill,
    ExtremeSubclassSkillBarResult,
    ExtremeSubclassTwoBarResult,
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


class _AsymmetricTwoBarService:
    @staticmethod
    def _bar(slot_counts, *, reviewed_critical: bool, id_offset: int):
        lines = [line for line, count in slot_counts for _ in range(count)]
        skills = []
        for index, line in enumerate(lines):
            name = f"{line} skill {index + 1}"
            if reviewed_critical and line == "assassination":
                name = "Relentless Focus"
                reviewed_critical = False
            skills.append(
                ExtremeSubclassBarSkill(
                    ability_id=id_offset + index,
                    base_ability_id=id_offset + 1000 + index,
                    name=name,
                    skill_line_id=line,
                    is_ultimate=index == 5,
                    morph=1,
                )
            )
        return ExtremeSubclassSkillBarResult(slot_counts=slot_counts, skills=tuple(skills))

    def materialize_two_bars(self, front_slot_counts, back_slot_counts, *, objective_key=""):
        if not front_slot_counts or not back_slot_counts:
            return None
        if sum(count for _, count in front_slot_counts) != 6:
            return None
        if sum(count for _, count in back_slot_counts) != 6:
            return None
        critical = objective_key in {"spell_critical", "weapon_critical"}
        return ExtremeSubclassTwoBarResult(
            front=self._bar(front_slot_counts, reviewed_critical=critical, id_offset=30000),
            back=self._bar(back_slot_counts, reviewed_critical=False, id_offset=40000),
        )


class _ResistanceSkillBarService:
    @staticmethod
    def _bar(slot_counts, id_offset: int):
        skills = []
        next_id = id_offset
        ultimate_assigned = False
        for line, count in slot_counts:
            for index in range(count):
                name = f"{line} skill {index + 1}"
                if line == "daedric_summoning" and index == 0:
                    name = "Bound Aegis"
                skills.append(
                    ExtremeSubclassBarSkill(
                        ability_id=next_id,
                        base_ability_id=next_id + 1000,
                        name=name,
                        skill_line_id=line,
                        is_ultimate=False,
                        morph=1,
                    )
                )
                next_id += 1
        if skills:
            last = skills[-1]
            skills[-1] = ExtremeSubclassBarSkill(
                ability_id=last.ability_id,
                base_ability_id=last.base_ability_id,
                name=last.name,
                skill_line_id=last.skill_line_id,
                is_ultimate=True,
                morph=last.morph,
            )
            ultimate_assigned = True
        if not ultimate_assigned or len(skills) != 6:
            return None
        return ExtremeSubclassSkillBarResult(slot_counts=slot_counts, skills=tuple(skills))

    def materialize_two_bars(self, front_slot_counts, back_slot_counts, *, objective_key=""):
        front = self._bar(front_slot_counts, 50000)
        back = self._bar(back_slot_counts, 60000)
        if front is None or back is None:
            return None
        return ExtremeSubclassTwoBarResult(front=front, back=back)


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
    assert len(best.front_skill_bar_names) == 6
    assert len(best.back_skill_bar_names) == 6
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


def test_joint_search_can_trade_one_passive_slot_for_stronger_reviewed_skill(tmp_path, monkeypatch):
    service = ExtremeClassRouteComparisonService(
        _database(tmp_path),
        skill_bar_service=_ResistanceSkillBarService(),
    )

    monkeypatch.setattr(
        "services.extreme_class_route_comparison_service.ExtremeClassConfigurationService.all_candidates",
        lambda: [
            type(
                "Config",
                (),
                {
                    "is_pure_class": False,
                    "base_class": CharacterClass.SORCERER,
                    "equipped_skill_lines": (
                        "winters_embrace",
                        "daedric_summoning",
                        "storm_calling",
                    ),
                },
            )()
        ],
    )
    monkeypatch.setattr(service.mastery_pairs, "best_pure_class_routes", lambda *args, **kwargs: ())

    result = service.compare("physical_resistance")
    best = result.best_reviewed_subclass_lower_bound

    assert best is not None
    assert dict(best.slot_counts)["winters_embrace"] == 5
    assert dict(best.slot_counts)["daedric_summoning"] == 1
    assert "Bound Aegis" in best.skill_bar_names
    assert any("Frozen Armor (5" in source for source in best.reviewed_sources)
    assert any("Bound Aegis" in source for source in best.reviewed_sources)
    assert best.projected_delta == pytest.approx(9174.0)


def test_either_bar_skill_scores_from_front_even_when_back_is_active(tmp_path):
    service = ExtremeClassRouteComparisonService(
        _database(tmp_path),
        skill_bar_service=_AsymmetricTwoBarService(),
    )

    front = service.compare("spell_critical", active_bar="front")
    back = service.compare("spell_critical", active_bar="back")
    front_best = front.best_reviewed_subclass_lower_bound
    back_best = back.best_reviewed_subclass_lower_bound

    assert front_best is not None
    assert back_best is not None
    assert "Relentless Focus" in front_best.front_skill_bar_names
    assert "Relentless Focus" not in front_best.back_skill_bar_names
    assert front_best.skill_bar_names == front_best.front_skill_bar_names
    assert back_best.skill_bar_names == back_best.back_skill_bar_names
    assert front_best.projected_delta == back_best.projected_delta
    assert any("Relentless Focus" in source for source in front_best.reviewed_sources)
    assert any("Relentless Focus" in source for source in back_best.reviewed_sources)


def test_invalid_active_bar_is_rejected(tmp_path):
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="active_bar"):
        service.compare("spell_critical", active_bar="both")


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
