import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.build_calculation_context import (
    BuildCalculationContext,
    CombatEnvironment,
    ScalingRule,
)
from minmax.character_progression import AttributeAllocation, CharacterProgression


def _context() -> BuildCalculationContext:
    attributes = AttributeAllocation(health=20, magicka=22, stamina=22)
    progression = CharacterProgression(attributes=attributes)
    state = BaseCharacterCalculator().calculate(attributes=attributes)
    return BuildCalculationContext(
        character_id="character-1",
        build_id="build-1",
        progression=progression,
        character_state=state,
        selected_skills=("Healing Seed", "Illustrious Healing"),
    )


def test_context_defaults_to_pve_monster_target():
    context = _context()
    assert context.environment is CombatEnvironment.PVE
    assert context.target_type == "monster"
    assert context.target_count == 1


def test_context_resolves_scaling_rules_from_character_state():
    context = _context()

    assert context.resolve_scaling(ScalingRule.HEALTH) == context.character_state.max_health
    assert context.resolve_scaling(ScalingRule.MAGICKA) == context.character_state.max_magicka
    assert context.resolve_scaling(ScalingRule.STAMINA) == context.character_state.max_stamina
    assert context.resolve_scaling(ScalingRule.HIGHEST_RESOURCE) == 14442
    assert context.resolve_scaling(ScalingRule.HIGHEST_ATTRIBUTE) == 18440
    assert context.resolve_scaling(ScalingRule.FIXED) == 0


def test_context_rejects_invalid_identity_and_targets():
    context = _context()
    with pytest.raises(ValueError):
        BuildCalculationContext("", context.build_id, context.progression, context.character_state)
    with pytest.raises(ValueError):
        BuildCalculationContext(context.character_id, "", context.progression, context.character_state)
    with pytest.raises(ValueError):
        BuildCalculationContext(context.character_id, context.build_id, context.progression, context.character_state, target_count=0)
    with pytest.raises(ValueError):
        BuildCalculationContext(context.character_id, context.build_id, context.progression, context.character_state, fight_duration=0)


def test_context_can_represent_pvp_without_changing_character_state():
    base = _context()
    pvp = BuildCalculationContext(
        character_id=base.character_id,
        build_id=base.build_id,
        progression=base.progression,
        character_state=base.character_state,
        environment=CombatEnvironment.PVP,
        target_type="player",
    )

    assert pvp.environment is CombatEnvironment.PVP
    assert pvp.target_type == "player"
    assert pvp.character_state == base.character_state
