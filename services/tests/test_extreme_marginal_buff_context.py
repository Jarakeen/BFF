from __future__ import annotations

from services import extreme_subclass_skill_bar_service as module
from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService
from services.extreme_subclass_skill_bar_service import ExtremeSubclassSkillBarService
from services.named_buff_resolution_service import NamedBuffContribution


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


def _major_sorcery_potion() -> NamedBuffContribution:
    return NamedBuffContribution(
        stacking_key="major_sorcery",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Potion: Major Sorcery",
        source_kind="potion",
    )


def test_skill_major_sorcery_has_zero_marginal_value_when_potion_already_supplies_it():
    potion = _major_sorcery_potion()

    without_potion = ExtremeSkillStandingEffectService.marginal_score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
        reference_value=5000.0,
    )
    with_potion = ExtremeSkillStandingEffectService.marginal_score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
        reference_value=5000.0,
        external_effects=(potion,),
    )

    assert without_potion == 1000.0
    assert with_potion == 0.0


def test_external_major_sorcery_stops_tome_bearer_winning_morph_choice(monkeypatch, tmp_path):
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

    without_external = service.materialize(
        (("herald_of_the_tome", 6),),
        objective_key="spell_damage",
        reference_value=5000.0,
    )
    with_external = service.materialize(
        (("herald_of_the_tome", 6),),
        objective_key="spell_damage",
        reference_value=5000.0,
        external_effects=(_major_sorcery_potion(),),
    )

    assert without_external is not None
    assert with_external is not None
    assert "Tome-Bearer's Inspiration" in without_external.names
    assert "Other Morph" not in without_external.names
    assert "Other Morph" in with_external.names
    assert "Tome-Bearer's Inspiration" not in with_external.names


def test_minor_sorcery_does_not_suppress_major_sorcery_marginal_value():
    minor = NamedBuffContribution(
        stacking_key="minor_sorcery",
        objective_key="spell_damage",
        projected_delta=500.0,
        source="Group provider: Minor Sorcery",
        source_kind="group_provider",
    )

    marginal = ExtremeSkillStandingEffectService.marginal_score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
        reference_value=5000.0,
        external_effects=(minor,),
    )

    assert marginal == 1000.0
