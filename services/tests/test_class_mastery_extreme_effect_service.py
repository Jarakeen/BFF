from __future__ import annotations

import pytest

from services.class_mastery_classification_service import ClassMasteryBoundary
from services.class_mastery_extreme_effect_service import ClassMasteryExtremeEffectService
from services.class_mastery_repository import ClassMasteryPassive


def _passive(class_name: str, name: str) -> ClassMasteryPassive:
    return ClassMasteryPassive(
        skill_id=1,
        base_ability_id=100,
        name=name,
        class_name=class_name,
        description="",
    )


def _by_key(rows):
    return {row.objective_key: row for row in rows}


def test_nightblade_above_and_beyond_is_reviewed_standing_critical_damage():
    rows = ClassMasteryExtremeEffectService.contributions(
        _passive("Nightblade", "Above and Beyond")
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.objective_key == "critical_damage"
    assert row.additive_ratio == pytest.approx(0.25)
    assert row.boundary is ClassMasteryBoundary.STANDING_SELF_CONTAINED


def test_nightblade_eye_for_exploitation_is_target_state_power_cap():
    rows = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Nightblade", "An Eye for Exploitation")
        )
    )

    assert rows["weapon_damage"].flat == pytest.approx(2000.0)
    assert rows["spell_damage"].flat == pytest.approx(2000.0)
    assert rows["spell_damage"].boundary is ClassMasteryBoundary.TARGET_STATE_DEPENDENT


def test_templar_bright_harbinger_uses_doubled_self_value():
    rows = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Templar", "Bright Harbinger")
        )
    )

    assert rows["weapon_damage"].flat == pytest.approx(600.0)
    assert rows["spell_damage"].flat == pytest.approx(600.0)
    assert rows["spell_damage"].boundary is ClassMasteryBoundary.COMBAT_STATE_DEPENDENT


def test_warden_wild_adaptation_uses_tooltip_cap_not_uncapped_status_count():
    rows = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Warden", "Wild Adaptation")
        )
    )

    assert rows["spell_damage"].flat == pytest.approx(1665.0)
    assert rows["spell_damage"].boundary is ClassMasteryBoundary.TARGET_STATE_DEPENDENT


def test_necromancer_nothing_wasted_uses_ten_stack_percent_cap():
    rows = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Necromancer", "Nothing Wasted")
        )
    )

    assert rows["max_health"].percent == pytest.approx(0.20)
    assert rows["weapon_damage"].percent == pytest.approx(0.20)
    assert rows["spell_damage"].percent == pytest.approx(0.20)


def test_sorcerer_font_of_power_scales_from_higher_max_resource():
    rows = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Sorcerer", "Font of Power"),
            higher_max_resource=35000,
        )
    )

    # 6% base + twenty complete 1750-resource steps = 26%.
    assert rows["weapon_damage"].percent == pytest.approx(0.26)
    assert rows["spell_damage"].percent == pytest.approx(0.26)
    assert rows["spell_damage"].boundary is ClassMasteryBoundary.COMBAT_STATE_DEPENDENT


def test_sorcerer_font_of_power_refuses_to_guess_without_resource_input():
    rows = ClassMasteryExtremeEffectService.contributions(
        _passive("Sorcerer", "Font of Power")
    )

    assert rows == ()


def test_recovery_masteries_are_kept_as_combat_state_snapshots():
    sphere = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Sorcerer", "Sphere of Influence")
        )
    )
    devout = _by_key(
        ClassMasteryExtremeEffectService.contributions(
            _passive("Templar", "Devout Guardian")
        )
    )

    assert sphere["magicka_recovery"].flat == pytest.approx(225.0)
    assert devout["magicka_recovery"].flat == pytest.approx(300.0)
    assert sphere["magicka_recovery"].boundary is ClassMasteryBoundary.COMBAT_STATE_DEPENDENT


def test_unknown_mastery_never_invents_an_effect():
    rows = ClassMasteryExtremeEffectService.contributions(
        _passive("Arcanist", "Made Up Mastery")
    )

    assert rows == ()
