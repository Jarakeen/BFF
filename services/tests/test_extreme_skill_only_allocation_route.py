from __future__ import annotations

import sqlite3

from minmax.character_build.character_class import CharacterClass
from services import extreme_class_route_comparison_service as module
from services.extreme_class_route_comparison_service import ExtremeClassRouteComparisonService
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
        db.commit()
    return path


class _SkillOnlyBarService:
    def materialize_two_bars(
        self,
        front_slot_counts,
        back_slot_counts,
        *,
        objective_key="",
        reference_value=None,
        external_effects=(),
    ):
        if dict(front_slot_counts).get("herald_of_the_tome", 0) <= 0:
            return None

        def bar(slot_counts, offset):
            skills = (
                ExtremeSubclassBarSkill(
                    ability_id=offset + 1,
                    base_ability_id=offset + 101,
                    name="Tome-Bearer's Inspiration",
                    skill_line_id="herald_of_the_tome",
                    is_ultimate=False,
                    morph=1,
                ),
                ExtremeSubclassBarSkill(
                    ability_id=offset + 2,
                    base_ability_id=offset + 102,
                    name="Other One",
                    skill_line_id="herald_of_the_tome",
                    is_ultimate=False,
                    morph=1,
                ),
                ExtremeSubclassBarSkill(
                    ability_id=offset + 3,
                    base_ability_id=offset + 103,
                    name="Other Two",
                    skill_line_id="herald_of_the_tome",
                    is_ultimate=False,
                    morph=1,
                ),
                ExtremeSubclassBarSkill(
                    ability_id=offset + 4,
                    base_ability_id=offset + 104,
                    name="Other Three",
                    skill_line_id="herald_of_the_tome",
                    is_ultimate=False,
                    morph=1,
                ),
                ExtremeSubclassBarSkill(
                    ability_id=offset + 5,
                    base_ability_id=offset + 105,
                    name="Other Four",
                    skill_line_id="herald_of_the_tome",
                    is_ultimate=False,
                    morph=1,
                ),
                ExtremeSubclassBarSkill(
                    ability_id=offset + 6,
                    base_ability_id=offset + 106,
                    name="Herald Ultimate",
                    skill_line_id="herald_of_the_tome",
                    is_ultimate=True,
                    morph=1,
                ),
            )
            return ExtremeSubclassSkillBarResult(slot_counts=slot_counts, skills=skills)

        return ExtremeSubclassTwoBarResult(
            front=bar(front_slot_counts, 1000),
            back=bar(back_slot_counts, 2000),
        )


def test_skill_only_standing_effect_can_create_reviewed_subclass_lower_bound(monkeypatch, tmp_path):
    config = type(
        "Config",
        (),
        {
            "is_pure_class": False,
            "base_class": CharacterClass.ARCANIST,
            "equipped_skill_lines": (
                "herald_of_the_tome",
                "aedric_spear",
                "green_balance",
            ),
        },
    )()

    monkeypatch.setattr(module.ExtremeClassConfigurationService, "all_candidates", lambda: [config])

    service = ExtremeClassRouteComparisonService(
        _database(tmp_path),
        skill_bar_service=_SkillOnlyBarService(),
    )
    monkeypatch.setattr(service.mastery_pairs, "best_pure_class_routes", lambda *args, **kwargs: ())

    comparison = service.compare("spell_damage", reference_value=5000.0)
    route = comparison.best_reviewed_subclass_lower_bound

    assert route is not None
    assert route.projected_delta == 1000.0
    assert "Tome-Bearer's Inspiration" in route.front_skill_bar_names
    assert any("Major Brutality/Sorcery" in source for source in route.reviewed_sources)
