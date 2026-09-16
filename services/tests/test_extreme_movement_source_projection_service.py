from __future__ import annotations

import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId
from services.extreme_movement_source_projection_service import (
    ExtremeMovementSourceProjectionService,
)
from services.extreme_movement_state_service import ExtremeMovementStateService


def test_expedition_and_steed_share_canonical_movement_projection() -> None:
    major_expedition = effects_for_buff("Major Expedition")
    steed = Effect(
        stat=StatId.MOVEMENT_SPEED,
        operation=EffectOperation.ADD_PERCENT,
        value=10.0,
        unit=EffectUnit.PERCENT,
        source="Mundus: The Steed",
    )

    projection = ExtremeMovementSourceProjectionService.compose(
        named_buff_effects=tuple(("Major Expedition", effect) for effect in major_expedition),
        mundus_effects=(steed,),
    )

    assert projection.unresolved == ()
    assert projection.inputs.buff_movement_speed == pytest.approx(0.30)
    assert projection.inputs.mundus_movement_speed == pytest.approx(0.10)

    movement = ExtremeMovementStateService.evaluate("movement_speed", projection.inputs)
    assert movement.raw_multiplier == pytest.approx(1.40)
    assert movement.effective_multiplier == pytest.approx(1.40)


def test_minor_and_major_expedition_are_first_class_movement_stats() -> None:
    minor = effects_for_buff("Minor Expedition")
    major = effects_for_buff("Major Expedition")

    assert len(minor) == 1
    assert len(major) == 1
    assert minor[0].stat is StatId.MOVEMENT_SPEED
    assert minor[0].value == pytest.approx(0.15)
    assert major[0].stat is StatId.MOVEMENT_SPEED
    assert major[0].value == pytest.approx(0.30)


def test_non_movement_effect_fails_closed_in_movement_projection() -> None:
    projection = ExtremeMovementSourceProjectionService.compose(
        mundus_effects=(
            Effect(
                stat=StatId.HEALTH_RECOVERY,
                operation=EffectOperation.ADD,
                value=238.0,
                unit=EffectUnit.FLAT,
                source="Mundus: The Steed health branch",
            ),
        )
    )

    assert projection.inputs.mundus_movement_speed == 0.0
    assert projection.unresolved == (
        "Mundus: The Steed health branch: non-movement effect health_recovery",
    )
