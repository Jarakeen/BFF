from __future__ import annotations

from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService


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


def test_reviewed_crit_skill_does_not_fake_spell_damage():
    assert ExtremeSkillStandingEffectService.score("Relentless Focus", "spell_damage") == 0.0


def test_unknown_skill_remains_unscored():
    assert ExtremeSkillStandingEffectService.effects_for_skill("Some Unreviewed Skill") == ()
    assert ExtremeSkillStandingEffectService.score("Some Unreviewed Skill", "spell_critical") == 0.0
