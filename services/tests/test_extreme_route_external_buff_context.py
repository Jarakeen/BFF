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
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationResult
from services.named_buff_resolution_service import NamedBuffContribution


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


class _TomeBarService:
    def materialize_two_bars(
        self,
        front_slot_counts,
        back_slot_counts,
        *,
        objective_key="",
        reference_value=None,
        external_effects=(),
    ):
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


def _potion_major_sorcery():
    return NamedBuffContribution(
        stacking_key="major_sorcery",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Potion: Major Sorcery",
        source_kind="potion",
    )


def test_route_only_receives_marginal_skill_value_beyond_external_buff(monkeypatch, tmp_path):
    config = type(
        "Config",
        (),
        {
            "is_pure_class": False,
            "base_class": CharacterClass.ARCANIST,
            "equipped_skill_lines": (
                "herald_of_the_tome",
                "storm_calling",
                "winters_embrace",
            ),
        },
    )()
    allocation = ExtremeSubclassSlotAllocationResult(
        objective_key="spell_damage",
        equipped_skill_lines=config.equipped_skill_lines,
        slot_counts=(("herald_of_the_tome", 6),),
        projected_delta=100.0,
        reviewed_sources=("Synthetic reviewed line value",),
    )

    monkeypatch.setattr(module.ExtremeClassConfigurationService, "all_candidates", lambda: [config])
    monkeypatch.setattr(
        module.ExtremeSubclassSlotAllocationService,
        "reviewed_allocations",
        lambda *args, **kwargs: (allocation,),
    )

    service = ExtremeClassRouteComparisonService(
        _database(tmp_path),
        skill_bar_service=_TomeBarService(),
    )
    monkeypatch.setattr(service.mastery_pairs, "best_pure_class_routes", lambda *args, **kwargs: ())

    without_external = service.compare("spell_damage", reference_value=5000.0)
    with_external = service.compare(
        "spell_damage",
        reference_value=5000.0,
        external_effects=(_potion_major_sorcery(),),
    )

    assert without_external.best_reviewed_subclass_lower_bound is not None
    assert with_external.best_reviewed_subclass_lower_bound is not None
    assert without_external.best_reviewed_subclass_lower_bound.projected_delta == 1100.0
    assert with_external.best_reviewed_subclass_lower_bound.projected_delta == 100.0
