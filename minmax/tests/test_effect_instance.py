import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer


def test_identity_is_the_name_not_the_magnitude():
    a = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Masters Architect",
        magnitude=10,
    )
    b = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Zaans Redress",
        magnitude=10,
    )

    assert a.name == b.name
    assert a.source != b.source


def test_multiple_numerical_values_can_attach_to_one_named_effect():
    weak = EffectVariant(
        name="major_brittle",
        layer=EffectLayer.PROC,
        source="Frost Staff Heavy Attack",
        magnitude=10,
        duration=6.0,
        chance=0.25,
    )
    strong = EffectVariant(
        name="major_brittle",
        layer=EffectLayer.PROC,
        source="Ice Furnace",
        magnitude=10,
        duration=10.0,
        chance=1.0,
    )

    assert weak.name == strong.name
    assert weak.duration != strong.duration
    assert weak.chance != strong.chance


def test_magnitude_alone_never_defines_identity():
    same_value_different_effects = [
        EffectVariant(
            name="major_force", layer=EffectLayer.CAST, source="X", magnitude=430
        ),
        EffectVariant(
            name="major_courage", layer=EffectLayer.PROC, source="Y", magnitude=430
        ),
    ]
    names = {effect.name for effect in same_value_different_effects}
    assert names == {"major_force", "major_courage"}


def test_empty_name_is_rejected():
    with pytest.raises(ValueError):
        EffectVariant(name="", layer=EffectLayer.CAST, source="X")


def test_chance_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        EffectVariant(name="proc", layer=EffectLayer.PROC, source="X", chance=1.5)


def test_is_available_on_bar():
    front_only = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Masters Restoration Staff",
        active_bar=BarId.FRONT,
    )

    assert front_only.is_available_on(BarId.FRONT)
    assert not front_only.is_available_on(BarId.BACK)


def test_no_bar_requirement_is_available_on_either_bar():
    always = EffectVariant(name="weapon_damage_flat", layer=EffectLayer.SLOTTED, source="Glyph")

    assert always.is_available_on(BarId.FRONT)
    assert always.is_available_on(BarId.BACK)
