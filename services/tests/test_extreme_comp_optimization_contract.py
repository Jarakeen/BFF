from __future__ import annotations

from dataclasses import replace

import pytest

from services.extreme_build_catalog_service import ExtremeBuildCatalogService
from services.extreme_skill_standing_effect_service import (
    ExtremeSkillEffectScope,
    ExtremeSkillStandingEffect,
    ExtremeSkillStandingEffectService,
)
from services.named_buff_resolution_service import (
    NamedBuffContribution,
    NamedBuffResolutionService,
)


"""Shared mechanics contract for Comp Maker and optimization consumers.

These tests intentionally target source-neutral mechanics and invariants rather
than UI behavior or one frozen 'best build'. Comp Maker, Team Optimization, and
Extreme Build Lab should all be able to rely on the same rules for named buffs,
bar scope, marginal value, and reviewed passive formulas.
"""


def _buff(
    stacking_key: str,
    objective_key: str,
    projected_delta: float,
    source: str,
    source_kind: str,
) -> NamedBuffContribution:
    return NamedBuffContribution(
        stacking_key=stacking_key,
        objective_key=objective_key,
        projected_delta=projected_delta,
        source=source,
        source_kind=source_kind,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Major Sorcery", "major_sorcery"),
        (" major-sorcery ", "major_sorcery"),
        ("MAJOR   SORCERY", "major_sorcery"),
        ("Minor Resolve", "minor_resolve"),
    ],
)
def test_named_buff_identity_is_canonical_and_ui_spelling_neutral(raw, expected):
    assert NamedBuffResolutionService.canonical_key(raw) == expected


def test_same_named_buff_dedupes_across_skill_potion_set_and_group_sources():
    effects = (
        _buff("major_sorcery", "spell_damage", 400.0, "skill", "skill"),
        _buff("Major Sorcery", "spell_damage", 400.0, "potion", "potion"),
        _buff("major-sorcery", "spell_damage", 400.0, "set", "set"),
        _buff("major sorcery", "spell_damage", 400.0, "group", "group_provider"),
    )

    resolution = NamedBuffResolutionService.explain(effects, objective_key="spell_damage")

    assert len(resolution.selected) == 1
    assert resolution.selected[0].source == "group"
    assert len(resolution.suppressed) == 3
    assert {item.stacking_key for item in resolution.suppressed} == {"major_sorcery"}


def test_larger_same_named_buff_contribution_wins_regardless_of_source_kind():
    effects = (
        _buff("minor_resolve", "physical_resistance", 1000.0, "group", "group_provider"),
        _buff("minor_resolve", "physical_resistance", 2974.0, "Bound Aegis", "skill"),
    )

    selected = NamedBuffResolutionService.resolve(effects)

    assert len(selected) == 1
    assert selected[0].source == "Bound Aegis"
    assert selected[0].projected_delta == pytest.approx(2974.0)


def test_equal_same_named_buff_uses_deterministic_lexical_tiebreak():
    effects = (
        _buff("major_sorcery", "spell_damage", 400.0, "Zeta source", "set"),
        _buff("major_sorcery", "spell_damage", 400.0, "Alpha source", "potion"),
    )

    selected = NamedBuffResolutionService.resolve(effects)

    assert tuple(item.source for item in selected) == ("Alpha source",)


def test_major_and_minor_variants_stack_when_they_are_distinct_named_buffs():
    effects = (
        _buff("major_resolve", "physical_resistance", 5948.0, "Major Resolve", "skill"),
        _buff("minor_resolve", "physical_resistance", 2974.0, "Minor Resolve", "skill"),
    )

    score, sources = NamedBuffResolutionService.score(
        effects,
        objective_key="physical_resistance",
    )

    assert score == pytest.approx(8922.0)
    assert set(sources) == {"Major Resolve", "Minor Resolve"}


def test_same_named_buff_can_contribute_independently_to_different_objectives():
    effects = (
        _buff("minor_resolve", "physical_resistance", 2974.0, "Bound Aegis physical", "skill"),
        _buff("minor_resolve", "spell_resistance", 2974.0, "Bound Aegis spell", "skill"),
    )

    selected = NamedBuffResolutionService.resolve(effects)

    assert len(selected) == 2
    assert {item.objective_key for item in selected} == {
        "physical_resistance",
        "spell_resistance",
    }


def test_objective_filter_never_leaks_an_unrelated_buff_into_score():
    effects = (
        _buff("major_sorcery", "spell_damage", 400.0, "spell", "potion"),
        _buff("minor_resolve", "physical_resistance", 2974.0, "armor", "skill"),
    )

    score, sources = NamedBuffResolutionService.score(
        effects,
        objective_key="spell_damage",
    )

    assert score == pytest.approx(400.0)
    assert sources == ("spell",)


@pytest.mark.parametrize("active_bar", ["front", "back"])
def test_either_bar_minor_resolve_survives_when_bound_aegis_is_on_inactive_bar(active_bar):
    if active_bar == "front":
        front = ("Filler",)
        back = ("Bound Aegis",)
    else:
        front = ("Bound Aegis",)
        back = ("Filler",)

    score, sources = ExtremeSkillStandingEffectService.score_build_bars(
        front,
        back,
        "physical_resistance",
        active_bar=active_bar,
    )

    assert score == pytest.approx(ExtremeSkillStandingEffectService.MINOR_RESOLVE_ARMOR)
    assert any("Bound Aegis" in source for source in sources)


@pytest.mark.parametrize("active_bar", ["front", "back"])
def test_same_either_bar_skill_on_both_bars_is_not_double_counted(active_bar):
    score, sources = ExtremeSkillStandingEffectService.score_build_bars(
        ("Bound Aegis",),
        ("Bound Aegis",),
        "physical_resistance",
        active_bar=active_bar,
    )

    assert score == pytest.approx(ExtremeSkillStandingEffectService.MINOR_RESOLVE_ARMOR)
    assert len(sources) == 1


def test_external_duplicate_makes_skill_named_buff_marginal_value_zero():
    external = (
        _buff(
            "minor_resolve",
            "physical_resistance",
            ExtremeSkillStandingEffectService.MINOR_RESOLVE_ARMOR,
            "group Minor Resolve",
            "group_provider",
        ),
    )

    delta, sources, notes = ExtremeSkillStandingEffectService.marginal_score_build_bars_explained(
        ("Bound Aegis",),
        (),
        "physical_resistance",
        active_bar="front",
        external_effects=external,
    )

    assert delta == pytest.approx(0.0)
    assert len(sources) == 1
    assert notes
    assert any("minor resolve does not stack" in note.casefold() for note in notes)


def test_different_external_named_buff_stacks_with_skill_marginal_value():
    external = (
        _buff("major_resolve", "physical_resistance", 5948.0, "Major Resolve", "group_provider"),
    )

    delta, _, notes = ExtremeSkillStandingEffectService.marginal_score_build_bars_explained(
        (),
        ("Bound Aegis",),
        "physical_resistance",
        active_bar="front",
        external_effects=external,
    )

    assert delta == pytest.approx(ExtremeSkillStandingEffectService.MINOR_RESOLVE_ARMOR)
    assert notes == ()


def test_reference_dependent_major_sorcery_has_no_fake_value_without_reference_stat():
    assert ExtremeSkillStandingEffectService.score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
    ) == pytest.approx(0.0)


def test_reference_dependent_major_sorcery_uses_current_reference_stat():
    score = ExtremeSkillStandingEffectService.score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
        reference_value=3000.0,
    )

    assert score == pytest.approx(600.0)


def test_external_major_sorcery_removes_major_sorcery_skill_marginal_value():
    external = (
        _buff("major_sorcery", "spell_damage", 600.0, "spell power potion", "potion"),
    )

    delta = ExtremeSkillStandingEffectService.marginal_score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
        reference_value=3000.0,
        external_effects=external,
    )

    assert delta == pytest.approx(0.0)


def test_active_bar_only_effect_does_not_leak_from_inactive_bar(monkeypatch):
    original = ExtremeSkillStandingEffectService.effects_for_skill.__func__

    def fake_effects(cls, skill_name, *, reference_value=None):
        if skill_name == "Active Only Test":
            return (
                ExtremeSkillStandingEffect(
                    skill_name="Active Only Test",
                    objective_key="spell_damage",
                    projected_delta=123.0,
                    source="active-only synthetic",
                    scope=ExtremeSkillEffectScope.ACTIVE_BAR_SLOTTED,
                    stacking_key="active_only_test",
                ),
            )
        return original(cls, skill_name, reference_value=reference_value)

    monkeypatch.setattr(
        ExtremeSkillStandingEffectService,
        "effects_for_skill",
        classmethod(fake_effects),
    )

    inactive_score, _ = ExtremeSkillStandingEffectService.score_build_bars(
        (),
        ("Active Only Test",),
        "spell_damage",
        active_bar="front",
    )
    active_score, _ = ExtremeSkillStandingEffectService.score_build_bars(
        (),
        ("Active Only Test",),
        "spell_damage",
        active_bar="back",
    )

    assert inactive_score == pytest.approx(0.0)
    assert active_score == pytest.approx(123.0)


def test_runtime_activated_effect_is_not_credited_as_unconditional_standing_value(monkeypatch):
    original = ExtremeSkillStandingEffectService.effects_for_skill.__func__

    def fake_effects(cls, skill_name, *, reference_value=None):
        if skill_name == "Runtime Proc Test":
            return (
                ExtremeSkillStandingEffect(
                    skill_name="Runtime Proc Test",
                    objective_key="weapon_damage",
                    projected_delta=999.0,
                    source="runtime synthetic",
                    scope=ExtremeSkillEffectScope.ACTIVATED_RUNTIME,
                    stacking_key="runtime_proc_test",
                ),
            )
        return original(cls, skill_name, reference_value=reference_value)

    monkeypatch.setattr(
        ExtremeSkillStandingEffectService,
        "effects_for_skill",
        classmethod(fake_effects),
    )

    assert ExtremeSkillStandingEffectService.score(
        "Runtime Proc Test",
        "weapon_damage",
    ) == pytest.approx(0.0)


def test_invalid_active_bar_is_rejected_in_shared_bar_scoring():
    with pytest.raises(ValueError, match="active_bar must be 'front' or 'back'"):
        ExtremeSkillStandingEffectService.score_build_bars(
            (),
            (),
            "physical_resistance",
            active_bar="middle",
        )


def test_precomputed_expert_mage_formula_is_source_of_truth_for_spell_and_weapon_damage():
    lines = ("daedric_summoning", "dark_magic", "storm_calling")
    allocation = {
        "daedric_summoning": 0,
        "dark_magic": 0,
        "storm_calling": 6,
    }

    spell = ExtremeBuildCatalogService._passive_formula(lines, allocation, "spell_damage")
    weapon = ExtremeBuildCatalogService._passive_formula(lines, allocation, "weapon_damage")

    assert spell is not None and weapon is not None
    assert spell.flat == pytest.approx(648.0)
    assert weapon.flat == pytest.approx(648.0)
    assert spell.sources == ("Expert Mage (6 Sorcerer slots)",)
    assert weapon.sources == ("Expert Mage (6 Sorcerer slots)",)


def test_precomputed_frozen_armor_formula_is_symmetric_for_both_resistances():
    lines = ("animal_companions", "green_balance", "winters_embrace")
    allocation = {
        "animal_companions": 0,
        "green_balance": 0,
        "winters_embrace": 6,
    }

    physical = ExtremeBuildCatalogService._passive_formula(
        lines,
        allocation,
        "physical_resistance",
    )
    spell = ExtremeBuildCatalogService._passive_formula(
        lines,
        allocation,
        "spell_resistance",
    )

    assert physical is not None and spell is not None
    assert physical.flat == pytest.approx(7440.0)
    assert spell.flat == pytest.approx(7440.0)


def test_precomputed_flourish_stays_reference_dependent_instead_of_freezing_a_score():
    lines = ("animal_companions", "green_balance", "winters_embrace")
    allocation = {
        "animal_companions": 1,
        "green_balance": 5,
        "winters_embrace": 0,
    }

    formula = ExtremeBuildCatalogService._passive_formula(
        lines,
        allocation,
        "magicka_recovery",
    )

    assert formula is not None
    assert formula.flat == pytest.approx(0.0)
    assert formula.percent_of_reference == pytest.approx(0.20)
    assert formula.sources == ("Flourish (Animal Companions represented)",)


def test_precomputed_advanced_species_scales_with_number_of_animal_companion_slots():
    lines = ("animal_companions", "green_balance", "winters_embrace")
    one = ExtremeBuildCatalogService._passive_formula(
        lines,
        {"animal_companions": 1, "green_balance": 5, "winters_embrace": 0},
        "critical_damage",
    )
    six = ExtremeBuildCatalogService._passive_formula(
        lines,
        {"animal_companions": 6, "green_balance": 0, "winters_embrace": 0},
        "critical_damage",
    )

    assert one is not None and six is not None
    assert six.ratio == pytest.approx(one.ratio * 6.0)


def test_unreviewed_passive_objective_does_not_invent_a_formula():
    formula = ExtremeBuildCatalogService._passive_formula(
        ("animal_companions", "green_balance", "winters_embrace"),
        {"animal_companions": 6, "green_balance": 0, "winters_embrace": 0},
        "max_health",
    )

    assert formula is None
