import pytest

from minmax.effect_mapper import EffectMapper
from minmax.effects import EffectOperation, EffectUnit
from minmax.stat_ids import StatId


def test_health_recovery_maps_to_stat():
    effect = EffectMapper.create_additive(
        effect_type="health_recovery",
        value=169,
        unit="flat",
        source="Glyph of Health Recovery",
    )

    assert effect.stat == StatId.HEALTH_RECOVERY
    assert effect.operation == EffectOperation.ADD
    assert effect.value == 169
    assert effect.unit == EffectUnit.FLAT
    assert effect.source == "Glyph of Health Recovery"


def test_percent_unit_maps_correctly():
    effect = EffectMapper.create_additive(
        effect_type="healing_done",
        value=2.5,
        unit="percent",
        source="Chysolite",
    )

    assert effect.stat == StatId.HEALING_DONE
    assert effect.value == 2.5
    assert effect.unit == EffectUnit.PERCENT


def test_unknown_effect_type_fails():
    with pytest.raises(ValueError, match="Unsupported engine stat effect type"):
        EffectMapper.create_additive(
            effect_type="something_we_have_not_defined",
            value=10,
            unit="flat",
            source="Test",
        )