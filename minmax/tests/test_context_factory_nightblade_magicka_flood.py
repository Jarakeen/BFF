from __future__ import annotations

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild


class _SkillLines:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def skill_line_for_ability_name(self, name):
        return self.mapping.get(str(name))

    def passive_max_rank(self, name):
        if str(name) == "Magicka Flood":
            return 2
        return None


def _factory():
    return BuildCalculationContextFactory(
        skill_line_repository=_SkillLines({"Healthy Offering": "Siphoning"})
    )


def _progression(rank=2):
    return CharacterProgression(
        passive_ranks={"Magicka Flood": rank},
        passive_cp_points={},
    )


def test_factory_applies_magicka_flood_before_resource_state_is_built():
    context = _factory().build(
        character_id="nightblade",
        build_id="heal",
        build=PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Healthy Offering"],
        ),
        progression=_progression(),
        active_bar="front",
    )

    # Reviewed U50 Magicka Flood rank 2 is +6% Max Magicka/Stamina.
    assert context.character_state.max_magicka == 12720
    labels = [step.label for step in context.character_state.traces[next(
        stat for stat in context.character_state.traces if stat.value == "max_magicka"
    )].steps]
    assert "Nightblade: Magicka Flood" in labels
    assert context.unresolved_gear_effects == ()


def test_factory_keeps_magicka_flood_active_bar_only():
    build = PlayerBuild(
        EsoClass="Nightblade",
        FrontBarSkills=["Combat Prayer"],
        BackBarSkills=["Healthy Offering"],
    )
    factory = _factory()

    front = factory.build(
        character_id="nightblade",
        build_id="front",
        build=build,
        progression=_progression(),
        active_bar="front",
    )
    back = factory.build(
        character_id="nightblade",
        build_id="back",
        build=build,
        progression=_progression(),
        active_bar="back",
    )

    assert front.character_state.max_magicka == 12000
    assert back.character_state.max_magicka == 12720


def test_factory_does_not_apply_partial_magicka_flood_rank():
    context = _factory().build(
        character_id="nightblade",
        build_id="partial",
        build=PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Healthy Offering"],
        ),
        progression=_progression(rank=1),
        active_bar="front",
    )

    assert context.character_state.max_magicka == 12000
    assert any(
        "Partial passive rank is not yet modeled: Magicka Flood 1/2" in message
        for message in context.unresolved_gear_effects
    )
