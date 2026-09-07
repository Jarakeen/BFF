from __future__ import annotations

import pytest

from services.extreme_build_catalog_service import ExtremeBuildCatalogService
from services.extreme_skill_standing_effect_service import (
    ExtremeSkillEffectScope,
    ExtremeSkillStandingEffectService,
)


@pytest.mark.parametrize(
    ("objective", "lines", "allocation", "field"),
    [
        (
            "critical_damage",
            ("animal_companions", "green_balance", "winters_embrace"),
            {"animal_companions": 6, "green_balance": 0, "winters_embrace": 0},
            "ratio",
        ),
        (
            "magicka_recovery",
            ("animal_companions", "green_balance", "winters_embrace"),
            {"animal_companions": 1, "green_balance": 5, "winters_embrace": 0},
            "percent_of_reference",
        ),
        (
            "stamina_recovery",
            ("animal_companions", "green_balance", "winters_embrace"),
            {"animal_companions": 1, "green_balance": 5, "winters_embrace": 0},
            "percent_of_reference",
        ),
        (
            "physical_resistance",
            ("animal_companions", "green_balance", "winters_embrace"),
            {"animal_companions": 0, "green_balance": 0, "winters_embrace": 6},
            "flat",
        ),
        (
            "spell_resistance",
            ("animal_companions", "green_balance", "winters_embrace"),
            {"animal_companions": 0, "green_balance": 0, "winters_embrace": 6},
            "flat",
        ),
        (
            "spell_damage",
            ("daedric_summoning", "dark_magic", "storm_calling"),
            {"daedric_summoning": 0, "dark_magic": 0, "storm_calling": 6},
            "flat",
        ),
        (
            "weapon_damage",
            ("daedric_summoning", "dark_magic", "storm_calling"),
            {"daedric_summoning": 0, "dark_magic": 0, "storm_calling": 6},
            "flat",
        ),
        (
            "spell_critical",
            ("assassination", "shadow", "siphoning"),
            {"assassination": 6, "shadow": 0, "siphoning": 0},
            "ratio",
        ),
        (
            "weapon_critical",
            ("assassination", "shadow", "siphoning"),
            {"assassination": 6, "shadow": 0, "siphoning": 0},
            "ratio",
        ),
    ],
)
def test_every_reviewed_passive_objective_has_positive_formula_when_its_mechanic_is_present(
    objective,
    lines,
    allocation,
    field,
):
    formula = ExtremeBuildCatalogService._passive_formula(lines, allocation, objective)

    assert formula is not None
    assert getattr(formula, field) > 0.0
    assert formula.sources


def test_twin_recovery_objectives_share_the_same_flourish_formula():
    lines = ("animal_companions", "green_balance", "winters_embrace")
    allocation = {"animal_companions": 1, "green_balance": 5, "winters_embrace": 0}

    magicka = ExtremeBuildCatalogService._passive_formula(lines, allocation, "magicka_recovery")
    stamina = ExtremeBuildCatalogService._passive_formula(lines, allocation, "stamina_recovery")

    assert magicka is not None and stamina is not None
    assert magicka.percent_of_reference == pytest.approx(stamina.percent_of_reference)
    assert magicka.sources == stamina.sources


def test_twin_critical_objectives_share_the_same_pressure_points_formula():
    lines = ("assassination", "shadow", "siphoning")
    allocation = {"assassination": 2, "shadow": 2, "siphoning": 2}

    spell = ExtremeBuildCatalogService._passive_formula(lines, allocation, "spell_critical")
    weapon = ExtremeBuildCatalogService._passive_formula(lines, allocation, "weapon_critical")

    assert spell is not None and weapon is not None
    assert spell.ratio == pytest.approx(weapon.ratio)
    assert spell.sources == weapon.sources


@pytest.mark.parametrize(
    "skill_name",
    [
        "Grim Focus",
        "Relentless Focus",
        "Merciless Resolve",
        "Bound Armaments",
    ],
)
def test_all_reviewed_major_crit_skill_families_are_either_bar_and_cover_both_crit_objectives(
    skill_name,
):
    effects = ExtremeSkillStandingEffectService.effects_for_skill(skill_name)

    assert {effect.objective_key for effect in effects} == {
        "spell_critical",
        "weapon_critical",
    }
    assert {effect.stacking_key for effect in effects} == {
        "major_prophecy",
        "major_savagery",
    }
    assert all(effect.scope is ExtremeSkillEffectScope.EITHER_BAR_SLOTTED for effect in effects)
    assert all(effect.projected_delta > 0.0 for effect in effects)


def test_bound_aegis_reviews_both_resistances_as_either_bar_minor_resolve():
    effects = ExtremeSkillStandingEffectService.effects_for_skill("Bound Aegis")

    assert {effect.objective_key for effect in effects} == {
        "physical_resistance",
        "spell_resistance",
    }
    assert {effect.stacking_key for effect in effects} == {"minor_resolve"}
    assert all(effect.scope is ExtremeSkillEffectScope.EITHER_BAR_SLOTTED for effect in effects)
    assert {effect.projected_delta for effect in effects} == {
        ExtremeSkillStandingEffectService.MINOR_RESOLVE_ARMOR
    }


@pytest.mark.parametrize(
    "skill_name",
    [
        "Tome-Bearer's Inspiration",
        "Inspired Scholarship",
        "Recuperative Treatise",
    ],
)
def test_all_reviewed_major_power_skill_families_require_reference_and_cover_both_power_objectives(
    skill_name,
):
    unresolved = ExtremeSkillStandingEffectService.effects_for_skill(skill_name)
    resolved = ExtremeSkillStandingEffectService.effects_for_skill(
        skill_name,
        reference_value=4000.0,
    )

    assert unresolved == ()
    assert {effect.objective_key for effect in resolved} == {
        "spell_damage",
        "weapon_damage",
    }
    assert {effect.stacking_key for effect in resolved} == {
        "major_sorcery",
        "major_brutality",
    }
    assert all(effect.scope is ExtremeSkillEffectScope.EITHER_BAR_SLOTTED for effect in resolved)
    assert {effect.projected_delta for effect in resolved} == {800.0}


def test_unreviewed_skill_name_remains_neutral_instead_of_guessing_tooltip_effects():
    assert ExtremeSkillStandingEffectService.effects_for_skill(
        "Definitely Not A Reviewed Skill"
    ) == ()
