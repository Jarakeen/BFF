from __future__ import annotations

import pytest

from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.item_base_stats import BaseItemStatResolver
from minmax.weapon_trait_effectiveness import WeaponTraitEffectivenessResolver
from models.build_model import GearSlot, PlayerBuild


def _staff(trait: str) -> PlayerBuild:
    return PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Inferno Staff",
            Trait=trait,
            Quality="Gold",
            Level="CP160",
        )
    )


def _resolve(trait: str, *, pieces: int):
    inputs = GearCalculationInputs(
        set_counts=(("Heartland Conqueror", pieces),),
    )
    return BaseItemStatResolver().apply(inputs, _staff(trait), active_bar="front")


def test_heartland_requires_five_active_pieces() -> None:
    four = WeaponTraitEffectivenessResolver.resolve((("Heartland Conqueror", 4),))
    five = WeaponTraitEffectivenessResolver.resolve((("Heartland Conqueror", 5),))

    assert four.multiplier == pytest.approx(1.0)
    assert not four.evidence
    assert five.multiplier == pytest.approx(2.0)
    assert five.evidence == (
        "Heartland Conqueror 5pc: Weapon Trait effectiveness increased by 100%",
    )


def test_heartland_doubles_nirnhoned_weapon_power_bonus() -> None:
    ordinary = _resolve("Nirnhoned", pieces=4)
    heartland = _resolve("Nirnhoned", pieces=5)

    ordinary_trait = ordinary.core.weapon_damage.flat[-1]
    heartland_trait = heartland.core.weapon_damage.flat[-1]
    assert ordinary_trait.value == pytest.approx(200.0)
    assert heartland_trait.value == pytest.approx(400.0)
    assert "x2 trait effectiveness" in heartland_trait.label


def test_heartland_doubles_precise_after_two_slot_weapon_scaling() -> None:
    ordinary = _resolve("Precise", pieces=4)
    heartland = _resolve("Precise", pieces=5)

    assert ordinary.core.weapon_critical.additive_after_percent[-1].value == pytest.approx(0.072)
    assert heartland.core.weapon_critical.additive_after_percent[-1].value == pytest.approx(0.144)
    assert heartland.core.spell_critical.additive_after_percent[-1].value == pytest.approx(0.144)


def test_heartland_doubles_sharpened_after_two_slot_weapon_scaling() -> None:
    ordinary = _resolve("Sharpened", pieces=4)
    heartland = _resolve("Sharpened", pieces=5)

    assert ordinary.core.physical_penetration.flat[-1].value == pytest.approx(3276.0)
    assert heartland.core.physical_penetration.flat[-1].value == pytest.approx(6552.0)
    assert heartland.core.spell_penetration.flat[-1].value == pytest.approx(6552.0)


def test_heartland_doubles_powered_after_two_slot_weapon_scaling() -> None:
    ordinary = _resolve("Powered", pieces=4)
    heartland = _resolve("Powered", pieces=5)

    assert ordinary.core.healing_done.additive_after_percent[-1].value == pytest.approx(0.09)
    assert heartland.core.healing_done.additive_after_percent[-1].value == pytest.approx(0.18)


def test_heartland_doubles_defending_after_two_slot_weapon_scaling() -> None:
    ordinary = _resolve("Defending", pieces=4)
    heartland = _resolve("Defending", pieces=5)

    assert ordinary.core.physical_resistance.flat[-1].value == pytest.approx(3276.0)
    assert heartland.core.physical_resistance.flat[-1].value == pytest.approx(6552.0)
    assert heartland.core.spell_resistance.flat[-1].value == pytest.approx(6552.0)
