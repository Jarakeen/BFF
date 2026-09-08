from __future__ import annotations

import sqlite3

import pytest

from models.build_model import PlayerBuild
from services.extreme_nightblade_class_mastery_healing_service import (
    ExtremeNightbladeClassMasteryHealingService,
)


ABOVE_ID = 101
EYE_ID = 102
ABOVE_DUPLICATE_ID = 103


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, name TEXT, skill_line TEXT)"
        )
        db.executemany(
            "INSERT INTO ability (ability_id, name, skill_line) VALUES (?, ?, ?)",
            (
                (ABOVE_ID, "Above and Beyond", "Nightblade Class Mastery"),
                (EYE_ID, "An Eye for Exploitation", "Nightblade Class Mastery"),
                (ABOVE_DUPLICATE_ID, "Above and Beyond", "Nightblade Class Mastery"),
            ),
        )
    return path


def _nightblade(*, mastery_ids=(), lines=()):
    return PlayerBuild(
        BuildName="Pure Nightblade",
        EsoClass="Nightblade",
        ClassSkillLines=list(lines),
        ClassMasteryAbilityIds=list(mastery_ids),
    )


def test_no_selected_mastery_is_a_valid_zero_contribution(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(),
        target_health_fraction=0.25,
    )

    assert result.selected_masteries == ()
    assert result.critical_healing_bonus == 0.0
    assert result.critical_healing_cap == pytest.approx(1.25)
    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == ()


def test_above_and_beyond_adds_pve_critical_healing_and_raises_cap(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(
            mastery_ids=(ABOVE_ID,),
            lines=("Assassination", "Shadow", "Siphoning"),
        ),
        target_health_fraction=0.25,
    )

    assert result.selected_masteries == ("Above and Beyond",)
    assert result.critical_healing_bonus == pytest.approx(0.25)
    assert result.critical_healing_cap == pytest.approx(1.55)
    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == ()


def test_above_and_beyond_uses_battle_spirit_reduced_bonus_but_same_cap(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(mastery_ids=(ABOVE_ID,)),
        target_health_fraction=0.25,
        battle_spirit_active=True,
    )

    assert result.critical_healing_bonus == pytest.approx(0.05)
    assert result.critical_healing_cap == pytest.approx(1.55)


def test_eye_for_exploitation_scales_power_with_heal_target_missing_health(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(mastery_ids=(EYE_ID,)),
        target_health_fraction=0.25,
    )

    assert result.critical_healing_bonus == 0.0
    assert result.weapon_spell_damage_bonus == pytest.approx(1500.0)
    assert result.unresolved == ()


def test_two_healing_relevant_masteries_can_be_selected_together(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(mastery_ids=(ABOVE_ID, EYE_ID)),
        target_health_fraction=0.25,
    )

    assert result.selected_masteries == (
        "Above and Beyond",
        "An Eye for Exploitation",
    )
    assert result.critical_healing_bonus == pytest.approx(0.25)
    assert result.critical_healing_cap == pytest.approx(1.55)
    assert result.weapon_spell_damage_bonus == pytest.approx(1500.0)
    assert result.unresolved == ()


def test_eye_for_exploitation_preserves_blocker_when_target_health_is_unknown(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(mastery_ids=(EYE_ID,)),
    )

    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == (
        "An Eye for Exploitation requires explicit heal-target Health fraction",
    )


def test_subclassed_nightblade_cannot_claim_class_mastery(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(
            mastery_ids=(ABOVE_ID, EYE_ID),
            lines=("Siphoning", "Green Balance", "Restoring Light"),
        ),
        target_health_fraction=0.25,
    )

    assert result.critical_healing_bonus == 0.0
    assert result.critical_healing_cap == pytest.approx(1.25)
    assert result.weapon_spell_damage_bonus == 0.0
    assert any("unavailable while subclassing" in message for message in result.unresolved)


def test_more_than_two_selected_masteries_is_invalid_and_contributes_nothing(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(mastery_ids=(ABOVE_ID, EYE_ID, ABOVE_DUPLICATE_ID)),
        target_health_fraction=0.25,
    )

    assert result.critical_healing_bonus == 0.0
    assert result.critical_healing_cap == pytest.approx(1.25)
    assert result.weapon_spell_damage_bonus == 0.0
    assert any("at most 2 selected passives" in message for message in result.unresolved)


def test_unknown_selected_ability_id_remains_explicit_blocker(tmp_path):
    result = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path)).resolve(
        build=_nightblade(mastery_ids=(999999,)),
        target_health_fraction=0.25,
    )

    assert result.critical_healing_bonus == 0.0
    assert result.weapon_spell_damage_bonus == 0.0
    assert result.unresolved == (
        "Class Mastery ability id 999999 is unresolved in canonical ability data",
    )


def test_eye_target_health_fraction_must_be_normalized(tmp_path):
    service = ExtremeNightbladeClassMasteryHealingService(_database(tmp_path))

    with pytest.raises(ValueError, match="target_health_fraction"):
        service.resolve(
            build=_nightblade(mastery_ids=(EYE_ID,)),
            target_health_fraction=1.01,
        )
