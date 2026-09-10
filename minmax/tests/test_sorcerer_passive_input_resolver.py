from __future__ import annotations

from dataclasses import replace

import pytest

from minmax.base_character_state import BaseCharacterCalculator, PercentContribution
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.sorcerer_passive_input_resolver import SorcererPassiveInputResolver
from models.build_model import PlayerBuild


class _SkillLines:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def skill_line_for_ability_name(self, name):
        return self.mapping.get(str(name))


def test_native_sorcerer_expert_summoner_adds_five_percent_magicka_and_stamina():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Sorcerer"),
        expert_summoner_owned=True,
    )

    assert result.magicka.skill_percent_contributions == (
        PercentContribution("Sorcerer: Expert Summoner", 0.05),
    )
    assert result.stamina.skill_percent_contributions == (
        PercentContribution("Sorcerer: Expert Summoner", 0.05),
    )
    state = BaseCharacterCalculator().calculate(
        magicka=result.magicka,
        stamina=result.stamina,
    )
    assert state.max_magicka == 12600
    assert state.max_stamina == 12600
    assert result.applied_effect_count == 2


def test_explicit_class_route_can_remove_native_daedric_summoning():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Storm Calling", "Green Balance"],
        ),
        expert_summoner_owned=True,
    )

    assert result.magicka.skill_percent_contributions == ()
    assert result.stamina.skill_percent_contributions == ()


def test_foreign_base_class_can_use_explicit_daedric_summoning_route():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Daedric Summoning", "Green Balance"],
        ),
        expert_summoner_owned=True,
    )

    assert result.magicka.skill_percent_contributions[-1].value == pytest.approx(0.05)
    assert result.stamina.skill_percent_contributions[-1].value == pytest.approx(0.05)


def test_unowned_expert_summoner_does_not_apply():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Sorcerer"),
        expert_summoner_owned=False,
    )

    assert result.magicka.skill_percent_contributions == ()
    assert result.stamina.skill_percent_contributions == ()


def test_expert_summoner_joins_existing_resource_percent_buckets_additively():
    resolver = SorcererPassiveInputResolver()
    baseline = GearCalculationInputs(
        magicka=replace(
            GearCalculationInputs().magicka,
            skill_percent_contributions=(PercentContribution("Existing Magicka", 0.08),),
        ),
        stamina=replace(
            GearCalculationInputs().stamina,
            skill_percent_contributions=(PercentContribution("Existing Stamina", 0.06),),
        ),
    )
    result = resolver.apply(
        baseline,
        PlayerBuild(EsoClass="Sorcerer"),
        expert_summoner_owned=True,
    )

    assert tuple(item.value for item in result.magicka.skill_percent_contributions) == pytest.approx(
        (0.08, 0.05)
    )
    assert tuple(item.value for item in result.stamina.skill_percent_contributions) == pytest.approx(
        (0.06, 0.05)
    )
    state = BaseCharacterCalculator().calculate(
        magicka=result.magicka,
        stamina=result.stamina,
    )
    assert state.max_magicka == 13560
    # 6% + 5% are one additive 11% bucket: 12,000 * 1.11 = exactly 13,320.
    # The calculator deliberately suppresses binary-float dust before ESO ceil.
    assert state.max_stamina == 13320


def test_expert_mage_adds_108_weapon_and_spell_damage_per_active_sorcerer_slot():
    resolver = SorcererPassiveInputResolver(
        _SkillLines(
            {
                "Dark Exchange": "Dark Magic",
                "Twilight Matriarch": "Daedric Summoning",
                "Power Surge": "Storm Calling",
                "Combat Prayer": "Restoration Staff",
            }
        )
    )
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Sorcerer",
            FrontBarSkills=[
                "Dark Exchange",
                "Twilight Matriarch",
                "Power Surge",
                "Combat Prayer",
            ],
        ),
        active_bar="front",
        expert_mage_owned=True,
    )

    assert result.core.weapon_damage.flat[-1].label == "Sorcerer: Expert Mage"
    assert result.core.weapon_damage.flat[-1].value == pytest.approx(324.0)
    assert result.core.spell_damage.flat[-1].value == pytest.approx(324.0)
    assert result.applied_effect_count == 2


def test_expert_mage_is_active_bar_only():
    resolver = SorcererPassiveInputResolver(
        _SkillLines({"Power Surge": "Storm Calling"})
    )
    build = PlayerBuild(
        EsoClass="Sorcerer",
        FrontBarSkills=["Combat Prayer"],
        BackBarSkills=["Power Surge"],
    )

    front = resolver.apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        expert_mage_owned=True,
    )
    back = resolver.apply(
        GearCalculationInputs(),
        build,
        active_bar="back",
        expert_mage_owned=True,
    )

    assert front.core.spell_damage.flat == ()
    assert back.core.spell_damage.flat[-1].value == pytest.approx(108.0)


def test_expert_mage_counts_only_sorcerer_lines_still_present_in_explicit_route():
    resolver = SorcererPassiveInputResolver(
        _SkillLines(
            {
                "Dark Exchange": "Dark Magic",
                "Power Surge": "Storm Calling",
                "Twilight Matriarch": "Daedric Summoning",
            }
        )
    )
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Storm Calling", "Green Balance"],
            FrontBarSkills=["Dark Exchange", "Power Surge", "Twilight Matriarch"],
        ),
        expert_mage_owned=True,
    )

    assert result.core.spell_damage.flat[-1].value == pytest.approx(216.0)


def test_expert_mage_preserves_unknown_slot_as_blocker_without_inventing_power():
    resolver = SorcererPassiveInputResolver(_SkillLines({}))
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Sorcerer", FrontBarSkills=["Mystery Skill"]),
        expert_mage_owned=True,
    )

    assert result.core.spell_damage.flat == ()
    assert any("Expert Mage slot count is unresolved" in message for message in result.unresolved)
