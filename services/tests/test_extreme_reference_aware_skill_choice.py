from __future__ import annotations

from services import extreme_subclass_skill_bar_service as module
from services.extreme_subclass_skill_bar_service import ExtremeSubclassSkillBarService


def _skill(
    ability_id: int,
    base_ability_id: int,
    name: str,
    *,
    ultimate: bool = False,
    morph: int = 1,
) -> dict:
    return {
        "ability_id": ability_id,
        "base_ability_id": base_ability_id,
        "name": name,
        "skill_line": "Herald of the Tome",
        "is_player": 1,
        "is_passive": 0,
        "is_crafted": 0,
        "base_mechanic": 8 if ultimate else 0,
        "morph": morph,
    }


def test_percentage_standing_skill_only_wins_when_reference_value_is_supplied(monkeypatch, tmp_path):
    rows = [
        _skill(101, 1001, "Other Morph", morph=1),
        _skill(102, 1001, "Tome-Bearer's Inspiration", morph=2),
        _skill(103, 1002, "Herald Two"),
        _skill(104, 1003, "Herald Three"),
        _skill(105, 1004, "Herald Four"),
        _skill(106, 1005, "Herald Five"),
        _skill(201, 2001, "Herald Ultimate", ultimate=True),
    ]
    monkeypatch.setattr(module, "load_skill_choices", lambda _path: rows)
    service = ExtremeSubclassSkillBarService(tmp_path / "eso.db")

    without_reference = service.materialize(
        (("herald_of_the_tome", 6),),
        objective_key="spell_damage",
    )
    with_reference = service.materialize(
        (("herald_of_the_tome", 6),),
        objective_key="spell_damage",
        reference_value=5000.0,
    )

    assert without_reference is not None
    assert with_reference is not None
    assert "Other Morph" in without_reference.names
    assert "Tome-Bearer's Inspiration" not in without_reference.names
    assert "Tome-Bearer's Inspiration" in with_reference.names
    assert "Other Morph" not in with_reference.names
