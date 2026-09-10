from __future__ import annotations

from minmax.base_character_state import BaseCharacterCalculator
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.necromancer_passive_input_resolver import NecromancerPassiveInputResolver
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _SkillLines:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def skill_line_for_ability_name(self, name):
        return self.mapping.get(str(name))


def _resolver(mapping=None):
    return NecromancerPassiveInputResolver(_SkillLines(mapping or {}))


def test_last_gasp_adds_named_flat_max_health_before_rounding() -> None:
    result = _resolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Necromancer"),
        last_gasp_rank=2,
        health_avarice_rank=0,
    )

    state = BaseCharacterCalculator().calculate(health=result.health)
    assert state.max_health == 18412
    labels = [step.label for step in state.traces[StatId.MAX_HEALTH].steps]
    assert "Necromancer: Last Gasp" in labels
    assert result.applied_effect_count == 1
    assert result.unresolved == ()


def test_health_avarice_counts_only_active_bar_bone_tyrant_slots() -> None:
    build = PlayerBuild(
        EsoClass="Necromancer",
        FrontBarSkills=["Bitter Harvest", "Bone Totem", "Combat Prayer"],
        BackBarSkills=["Beckoning Armor"],
    )
    resolver = _resolver(
        {
            "Bitter Harvest": "Bone Tyrant",
            "Bone Totem": "Bone Tyrant",
            "Combat Prayer": "Restoration Staff",
            "Beckoning Armor": "Bone Tyrant",
        }
    )

    front = resolver.apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        last_gasp_rank=0,
        health_avarice_rank=2,
    )
    back = resolver.apply(
        GearCalculationInputs(),
        build,
        active_bar="back",
        last_gasp_rank=0,
        health_avarice_rank=2,
    )

    assert front.core.healing_taken.additive_after_percent[-1].label == "Necromancer: Health Avarice"
    assert front.core.healing_taken.additive_after_percent[-1].value == 0.06
    assert back.core.healing_taken.additive_after_percent[-1].value == 0.03


def test_health_avarice_rank_one_uses_one_percent_per_slot() -> None:
    result = _resolver({"Bone Totem": "Bone Tyrant"}).apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Necromancer", FrontBarSkills=["Bone Totem"]),
        health_avarice_rank=1,
    )

    assert result.core.healing_taken.additive_after_percent[-1].value == 0.01


def test_explicit_subclass_route_is_authoritative() -> None:
    resolver = _resolver({"Bone Totem": "Bone Tyrant"})
    build = PlayerBuild(
        EsoClass="Necromancer",
        ClassSkillLines=["Grave Lord", "Living Death", "Siphoning"],
        FrontBarSkills=["Bone Totem"],
    )

    result = resolver.apply(
        GearCalculationInputs(),
        build,
        last_gasp_rank=2,
        health_avarice_rank=2,
    )

    assert result.health.skill_flat == 0.0
    assert result.core.healing_taken.additive_after_percent == ()
    assert result.applied_effect_count == 0


def test_foreign_class_can_receive_bone_tyrant_passives_from_explicit_route() -> None:
    resolver = _resolver({"Bone Totem": "Bone Tyrant"})
    build = PlayerBuild(
        EsoClass="Warden",
        ClassSkillLines=["Green Balance", "Bone Tyrant", "Winter's Embrace"],
        FrontBarSkills=["Bone Totem"],
    )

    result = resolver.apply(
        GearCalculationInputs(),
        build,
        last_gasp_rank=2,
        health_avarice_rank=2,
    )

    assert result.health.skill_flat == 2412.0
    assert result.core.healing_taken.additive_after_percent[-1].value == 0.03


def test_health_avarice_fails_closed_when_active_skill_line_is_unknown() -> None:
    result = _resolver({}).apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Necromancer", FrontBarSkills=["Unknown Skill"]),
        health_avarice_rank=2,
    )

    assert result.core.healing_taken.additive_after_percent == ()
    assert any("Health Avarice slot count is unresolved" in message for message in result.unresolved)
