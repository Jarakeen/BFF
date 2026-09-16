from __future__ import annotations

import pytest

from minmax.mundus_repository import U50_MUNDUS_EFFECTS
from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId


def test_movement_channels_are_first_class_stat_ids() -> None:
    assert StatId.MOVEMENT_SPEED.value == "movement_speed"
    assert StatId.SPRINT_SPEED.value == "sprint_speed"
    assert StatId.SNEAK_SPEED.value == "sneak_speed"


def test_expedition_uses_canonical_movement_stat_channel() -> None:
    minor = effects_for_buff("Minor Expedition")
    major = effects_for_buff("Major Expedition")

    assert len(minor) == 1
    assert len(major) == 1
    assert minor[0].stat is StatId.MOVEMENT_SPEED
    assert minor[0].bucket == "ratio_points"
    assert minor[0].value == pytest.approx(0.15)
    assert major[0].stat is StatId.MOVEMENT_SPEED
    assert major[0].bucket == "ratio_points"
    assert major[0].value == pytest.approx(0.30)


def test_steed_seed_uses_supported_canonical_movement_stat() -> None:
    rows = U50_MUNDUS_EFFECTS["The Steed"]
    movement = [row for row in rows if row[0] == StatId.MOVEMENT_SPEED.value]

    assert movement == [(StatId.MOVEMENT_SPEED.value, 10.0, "percent", 1, "")]
