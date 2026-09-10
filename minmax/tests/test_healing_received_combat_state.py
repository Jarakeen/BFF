from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.healing_received_combat_state import resolve_healing_received_combat_state
from models.build_model import PlayerBuild


def test_vitality_and_defile_resolve_as_additive_healing_received_ratio_points():
    result = resolve_healing_received_combat_state(
        CombatState(
            active_buffs=(
                "Minor Vitality",
                "Major Vitality",
                "Minor Defile",
                "Major Defile",
            )
        )
    )

    assert result.ratio_points == pytest.approx(0.0)
    assert result.multiplier == pytest.approx(1.0)
    assert result.sources == (
        "Minor Vitality",
        "Major Vitality",
        "Minor Defile",
        "Major Defile",
    )


def test_vitality_and_defile_are_known_component_layer_effects():
    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="build",
        build=PlayerBuild(),
        progression=CharacterProgression(),
        combat_state=CombatState(
            active_buffs=("Minor Vitality", "Major Vitality", "Minor Defile", "Major Defile")
        ),
    )

    assert context.unresolved_gear_effects == ()
    for name in ("Minor Vitality", "Major Vitality", "Minor Defile", "Major Defile"):
        assert context.combat_state.has_buff(name)


def test_major_and_minor_vitality_stack_in_healing_received_bucket():
    result = resolve_healing_received_combat_state(
        CombatState(active_buffs=("Minor Vitality", "Major Vitality"))
    )

    assert result.ratio_points == pytest.approx(0.18)
    assert result.multiplier == pytest.approx(1.18)
