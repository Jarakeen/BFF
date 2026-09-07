from __future__ import annotations

import pytest

from minmax.gear_stat_inputs import GearStatInputResolver
from services.extreme_subclass_line_effect_service import ExtremeSubclassLineEffectService


def _by_key(rows):
    return {row.objective_key: row for row in rows}


def test_assassination_scores_reviewed_pressure_points_maximum():
    rows = _by_key(ExtremeSubclassLineEffectService.contributions_for_line("assassination"))
    expected = GearStatInputResolver.critical_rating_to_ratio(438.0 * 6)

    assert rows["spell_critical"].additive_ratio == pytest.approx(expected)
    assert rows["weapon_critical"].additive_ratio == pytest.approx(expected)


def test_storm_calling_scores_reviewed_expert_mage_maximum():
    rows = _by_key(ExtremeSubclassLineEffectService.contributions_for_line("storm_calling"))

    assert rows["spell_damage"].flat == pytest.approx(108.0 * 6)
    assert rows["weapon_damage"].flat == pytest.approx(108.0 * 6)


def test_animal_companions_scores_flourish_and_advanced_species():
    rows = _by_key(ExtremeSubclassLineEffectService.contributions_for_line("animal_companions"))

    assert rows["critical_damage"].additive_ratio == pytest.approx(0.30)
    assert rows["magicka_recovery"].percent == pytest.approx(0.20)
    assert rows["stamina_recovery"].percent == pytest.approx(0.20)


def test_winters_embrace_scores_frozen_armor_maximum():
    rows = _by_key(ExtremeSubclassLineEffectService.contributions_for_line("winters_embrace"))

    assert rows["physical_resistance"].flat == pytest.approx(1240.0 * 6)
    assert rows["spell_resistance"].flat == pytest.approx(1240.0 * 6)


def test_unreviewed_line_does_not_become_zero_scored_mechanic():
    assert ExtremeSubclassLineEffectService.contributions_for_line("earthen_heart") == ()
    assert ExtremeSubclassLineEffectService.contribution_for_objective(
        "earthen_heart", "spell_damage"
    ) is None


def test_reviewed_line_catalog_is_explicit_and_stable():
    assert ExtremeSubclassLineEffectService.reviewed_lines() == (
        "animal_companions",
        "assassination",
        "storm_calling",
        "winters_embrace",
    )
