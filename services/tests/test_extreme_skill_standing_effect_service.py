from __future__ import annotations

from services.extreme_skill_standing_effect_service import (
    ExtremeSkillEffectScope,
    ExtremeSkillStandingEffect,
    ExtremeSkillStandingEffectService,
)
from services.named_buff_resolution_service import NamedBuffContribution


def test_relentless_focus_has_reviewed_major_critical_effect():
    spell = ExtremeSkillStandingEffectService.score("Relentless Focus", "spell_critical")
    weapon = ExtremeSkillStandingEffectService.score("Relentless Focus", "weapon_critical")

    assert spell > 0
    assert weapon == spell


def test_merciless_resolve_uses_same_reviewed_major_critical_effect():
    relentless = ExtremeSkillStandingEffectService.score("Relentless Focus", "spell_critical")
    merciless = ExtremeSkillStandingEffectService.score("Merciless Resolve", "spell_critical")

    assert merciless == relentless


def test_bound_armaments_uses_same_reviewed_major_critical_effect():
    relentless = ExtremeSkillStandingEffectService.score("Relentless Focus", "spell_critical")
    bound = ExtremeSkillStandingEffectService.score("Bound Armaments", "spell_critical")

    assert bound == relentless
    assert ExtremeSkillStandingEffectService.score("Bound Armaments", "weapon_critical") == bound


def test_bound_aegis_has_reviewed_minor_resolve_armor_effect():
    physical = ExtremeSkillStandingEffectService.score("Bound Aegis", "physical_resistance")
    spell = ExtremeSkillStandingEffectService.score("Bound Aegis", "spell_resistance")

    assert physical == 2974.0
    assert spell == physical


def test_bound_aegis_does_not_fake_critical_or_damage():
    assert ExtremeSkillStandingEffectService.score("Bound Aegis", "spell_critical") == 0.0
    assert ExtremeSkillStandingEffectService.score("Bound Aegis", "spell_damage") == 0.0


def test_tome_bearer_power_requires_reference_value():
    assert ExtremeSkillStandingEffectService.score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
    ) == 0.0
    assert ExtremeSkillStandingEffectService.score(
        "Tome-Bearer's Inspiration",
        "spell_damage",
        reference_value=5000.0,
    ) == 1000.0


def test_reviewed_either_bar_skills_are_classified_as_either_bar_scope():
    effects = ExtremeSkillStandingEffectService.effects_for_skill("Relentless Focus")

    assert effects
    assert all(effect.scope is ExtremeSkillEffectScope.EITHER_BAR_SLOTTED for effect in effects)


def test_either_bar_effect_applies_while_other_bar_is_active():
    front_score, _ = ExtremeSkillStandingEffectService.score_build_bars(
        ("Relentless Focus",),
        (),
        "spell_critical",
        active_bar="front",
    )
    back_score, _ = ExtremeSkillStandingEffectService.score_build_bars(
        ("Relentless Focus",),
        (),
        "spell_critical",
        active_bar="back",
    )

    assert front_score > 0
    assert back_score == front_score


def test_same_major_named_buff_does_not_stack_across_bars():
    one_score, _ = ExtremeSkillStandingEffectService.score_build_bars(
        ("Relentless Focus",),
        (),
        "spell_critical",
        active_bar="front",
    )
    duplicate_score, sources = ExtremeSkillStandingEffectService.score_build_bars(
        ("Relentless Focus",),
        ("Bound Armaments",),
        "spell_critical",
        active_bar="front",
    )

    assert duplicate_score == one_score
    assert len(sources) == 1


def test_major_and_minor_named_buffs_remain_distinct_stacking_keys():
    major = ExtremeSkillStandingEffect(
        skill_name="Major source",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Major Sorcery",
        scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
        stacking_key="major_sorcery",
    )
    minor = ExtremeSkillStandingEffect(
        skill_name="Minor source",
        objective_key="spell_damage",
        projected_delta=500.0,
        source="Minor Sorcery",
        scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
        stacking_key="minor_sorcery",
    )

    stacked = ExtremeSkillStandingEffectService.stack_effects((major, minor))

    assert len(stacked) == 2
    assert sum(effect.projected_delta for effect in stacked) == 1500.0


def test_duplicate_major_named_buff_collapses_regardless_of_source_label():
    skill = ExtremeSkillStandingEffect(
        skill_name="Skill source",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Skill grants Major Sorcery",
        scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
        stacking_key="major_sorcery",
    )
    potion = ExtremeSkillStandingEffect(
        skill_name="Potion source",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Potion grants Major Sorcery",
        scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
        stacking_key="major_sorcery",
    )

    stacked = ExtremeSkillStandingEffectService.stack_effects((skill, potion))

    assert len(stacked) == 1
    assert stacked[0].projected_delta == 1000.0


def test_external_potion_major_sorcery_does_not_double_skill_major_sorcery():
    potion = NamedBuffContribution(
        stacking_key="major_sorcery",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Essence of Spell Power: Major Sorcery",
        source_kind="potion",
    )

    score, sources = ExtremeSkillStandingEffectService.score_build_bars(
        ("Tome-Bearer's Inspiration",),
        (),
        "spell_damage",
        active_bar="front",
        reference_value=5000.0,
        external_effects=(potion,),
    )

    assert score == 1000.0
    assert len(sources) == 1


def test_external_minor_sorcery_stacks_with_skill_major_sorcery():
    minor = NamedBuffContribution(
        stacking_key="minor_sorcery",
        objective_key="spell_damage",
        projected_delta=500.0,
        source="Group provider: Minor Sorcery",
        source_kind="group_provider",
    )

    score, sources = ExtremeSkillStandingEffectService.score_build_bars(
        ("Tome-Bearer's Inspiration",),
        (),
        "spell_damage",
        active_bar="back",
        reference_value=5000.0,
        external_effects=(minor,),
    )

    assert score == 1500.0
    assert len(sources) == 2


def test_reviewed_crit_skill_does_not_fake_spell_damage():
    assert ExtremeSkillStandingEffectService.score("Relentless Focus", "spell_damage") == 0.0


def test_unknown_skill_remains_unscored():
    assert ExtremeSkillStandingEffectService.effects_for_skill("Some Unreviewed Skill") == ()
    assert ExtremeSkillStandingEffectService.score("Some Unreviewed Skill", "spell_critical") == 0.0
