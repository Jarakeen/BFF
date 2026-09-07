from __future__ import annotations

from services import extreme_subclass_skill_bar_service as module
from services.extreme_subclass_skill_bar_service import ExtremeSubclassSkillBarService


def _skill(
    ability_id: int,
    base_ability_id: int,
    name: str,
    line: str,
    *,
    ultimate: bool = False,
    morph: int = 1,
) -> dict:
    return {
        "ability_id": ability_id,
        "base_ability_id": base_ability_id,
        "name": name,
        "skill_line": line,
        "is_player": 1,
        "is_passive": 0,
        "is_crafted": 0,
        "base_mechanic": 8 if ultimate else 0,
        "morph": morph,
    }


def test_canonical_line_identity_handles_display_punctuation():
    assert ExtremeSubclassSkillBarService.canonical_line_id("Winter's Embrace") == "winters_embrace"
    assert ExtremeSubclassSkillBarService.canonical_line_id("Dawn's Wrath") == "dawns_wrath"
    assert ExtremeSubclassSkillBarService.canonical_line_id("Storm Calling") == "storm_calling"


def test_materializes_five_normal_skills_and_one_ultimate(monkeypatch, tmp_path):
    rows = [
        _skill(101 + index, 1001 + index, f"Storm Skill {index}", "Storm Calling")
        for index in range(5)
    ] + [
        _skill(201, 2001, "Storm Ultimate", "Storm Calling", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    result = service.materialize((("storm_calling", 6),))

    assert result is not None
    assert len(result.skills) == 6
    assert sum(1 for skill in result.skills if skill.is_ultimate) == 1
    assert result.skills[-1].name == "Storm Ultimate"
    assert all(skill.skill_line_id == "storm_calling" for skill in result.skills)


def test_materializes_mixed_line_allocation_with_ultimate_from_represented_line(monkeypatch, tmp_path):
    rows = [
        _skill(101, 1001, "Storm One", "Storm Calling"),
        _skill(102, 1002, "Storm Two", "Storm Calling"),
        _skill(103, 1003, "Storm Three", "Storm Calling"),
        _skill(104, 1004, "Storm Four", "Storm Calling"),
        _skill(105, 1005, "Storm Five", "Storm Calling"),
        _skill(201, 2001, "Animal One", "Animal Companions"),
        _skill(202, 2002, "Animal Ultimate", "Animal Companions", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    result = service.materialize((("storm_calling", 5), ("animal_companions", 1)))

    assert result is not None
    assert sum(1 for skill in result.skills if skill.skill_line_id == "storm_calling") == 5
    assert sum(1 for skill in result.skills if skill.skill_line_id == "animal_companions") == 1
    assert result.skills[-1].name == "Animal Ultimate"


def test_each_purchased_subclass_line_may_supply_the_single_bar_ultimate(monkeypatch, tmp_path):
    rows = [
        _skill(101, 1001, "Assassin One", "Assassination"),
        _skill(102, 1002, "Assassin Two", "Assassination"),
        _skill(103, 1003, "Storm One", "Storm Calling"),
        _skill(104, 1004, "Storm Two", "Storm Calling"),
        _skill(105, 1005, "Animal One", "Animal Companions"),
        _skill(201, 2001, "Assassination Ultimate", "Assassination", ultimate=True),
        _skill(202, 2002, "Storm Ultimate", "Storm Calling", ultimate=True),
        _skill(203, 2003, "Animal Ultimate", "Animal Companions", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    result = service.materialize(
        (("assassination", 2), ("storm_calling", 2), ("animal_companions", 2))
    )

    assert result is not None
    assert len(result.skills) == 6
    assert sum(1 for skill in result.skills if skill.is_ultimate) == 1
    assert result.skills[-1].skill_line_id in {
        "assassination",
        "storm_calling",
        "animal_companions",
    }


def test_same_ultimate_may_be_slotted_on_both_bars(monkeypatch, tmp_path):
    rows = [
        _skill(101 + index, 1001 + index, f"Assassin Skill {index}", "Assassination")
        for index in range(5)
    ] + [
        _skill(201, 2001, "Assassination Ultimate", "Assassination", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    result = service.materialize_two_bars(
        (("assassination", 6),),
        (("assassination", 6),),
    )

    assert result is not None
    assert result.front.skills[-1].ability_id == 201
    assert result.back.skills[-1].ability_id == 201
    assert result.front.skills[-1].name == "Assassination Ultimate"
    assert result.back.skills[-1].name == "Assassination Ultimate"


def test_rejects_allocation_without_a_legal_ultimate(monkeypatch, tmp_path):
    rows = [
        _skill(101 + index, 1001 + index, f"Storm Skill {index}", "Storm Calling")
        for index in range(6)
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    assert service.materialize((("storm_calling", 6),)) is None


def test_base_and_morph_from_same_family_do_not_fill_two_slots(monkeypatch, tmp_path):
    rows = [
        _skill(101, 1001, "Base Skill", "Storm Calling", morph=0),
        _skill(102, 1001, "Morphed Skill", "Storm Calling", morph=1),
        _skill(103, 1002, "Skill Two", "Storm Calling"),
        _skill(104, 1003, "Skill Three", "Storm Calling"),
        _skill(105, 1004, "Skill Four", "Storm Calling"),
        _skill(201, 2001, "Storm Ultimate", "Storm Calling", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    assert service.materialize((("storm_calling", 6),)) is None


def test_morph_is_preferred_as_representative_within_one_base_family(monkeypatch, tmp_path):
    rows = [
        _skill(101, 1001, "Base Skill", "Storm Calling", morph=0),
        _skill(102, 1001, "Morphed Skill", "Storm Calling", morph=1),
        _skill(103, 1002, "Skill Two", "Storm Calling"),
        _skill(104, 1003, "Skill Three", "Storm Calling"),
        _skill(105, 1004, "Skill Four", "Storm Calling"),
        _skill(106, 1005, "Skill Five", "Storm Calling"),
        _skill(201, 2001, "Storm Ultimate", "Storm Calling", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    result = service.materialize((("storm_calling", 6),))

    assert result is not None
    assert "Morphed Skill" in result.names
    assert "Base Skill" not in result.names


def test_objective_prefers_reviewed_critical_morph_within_family(monkeypatch, tmp_path):
    rows = [
        _skill(101, 1001, "Other Morph", "Assassination", morph=1),
        _skill(102, 1001, "Relentless Focus", "Assassination", morph=2),
        _skill(103, 1002, "Assassin Two", "Assassination"),
        _skill(104, 1003, "Assassin Three", "Assassination"),
        _skill(105, 1004, "Assassin Four", "Assassination"),
        _skill(106, 1005, "Assassin Five", "Assassination"),
        _skill(201, 2001, "Assassination Ultimate", "Assassination", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    result = service.materialize(
        (("assassination", 6),),
        objective_key="spell_critical",
    )

    assert result is not None
    assert "Relentless Focus" in result.names
    assert "Other Morph" not in result.names
