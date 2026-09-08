from __future__ import annotations

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild


class _SkillLines:
    @staticmethod
    def passive_max_rank(name):
        if str(name) == "Expert Summoner":
            return 2
        return None

    @staticmethod
    def skill_line_for_ability_name(_name):
        return None


def _factory():
    return BuildCalculationContextFactory(skill_line_repository=_SkillLines())


def _progression(rank=2):
    return CharacterProgression(
        passive_ranks={"Expert Summoner": rank},
        passive_cp_points={},
    )


def test_factory_applies_expert_summoner_before_resource_state_is_built():
    context = _factory().build(
        character_id="sorcerer",
        build_id="heal",
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=_progression(),
    )

    assert context.character_state.max_magicka == 12600
    assert context.character_state.max_stamina == 12600
    magicka_labels = [
        step.label
        for stat, trace in context.character_state.traces.items()
        if stat.value == "max_magicka"
        for step in trace.steps
    ]
    stamina_labels = [
        step.label
        for stat, trace in context.character_state.traces.items()
        if stat.value == "max_stamina"
        for step in trace.steps
    ]
    assert "Sorcerer: Expert Summoner" in magicka_labels
    assert "Sorcerer: Expert Summoner" in stamina_labels
    assert context.unresolved_gear_effects == ()


def test_factory_explicit_route_can_remove_native_daedric_summoning():
    context = _factory().build(
        character_id="sorcerer",
        build_id="no-daedric",
        build=PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Storm Calling", "Green Balance"],
        ),
        progression=_progression(),
    )

    assert context.character_state.max_magicka == 12000
    assert context.character_state.max_stamina == 12000
    assert context.unresolved_gear_effects == ()


def test_factory_foreign_class_can_gain_expert_summoner_through_subclass_route():
    context = _factory().build(
        character_id="templar",
        build_id="daedric-subclass",
        build=PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Daedric Summoning", "Green Balance"],
        ),
        progression=_progression(),
    )

    assert context.character_state.max_magicka == 12600
    assert context.character_state.max_stamina == 12600
    assert context.unresolved_gear_effects == ()


def test_factory_does_not_apply_partial_expert_summoner_rank():
    context = _factory().build(
        character_id="sorcerer",
        build_id="partial",
        build=PlayerBuild(EsoClass="Sorcerer"),
        progression=_progression(rank=1),
    )

    assert context.character_state.max_magicka == 12000
    assert context.character_state.max_stamina == 12000
    assert any(
        "Partial passive rank is not yet modeled: Expert Summoner 1/2" in message
        for message in context.unresolved_gear_effects
    )
