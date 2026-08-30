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


@pytest.mark.parametrize(
    ("effect_type", "expected"),
    [
        ("weapon_damage", StatId.WEAPON_DAMAGE),
        ("spell_damage", StatId.SPELL_DAMAGE),
        ("physical_resistance", StatId.PHYSICAL_RESISTANCE),
        ("spell_resistance", StatId.SPELL_RESISTANCE),
        ("physical_penetration", StatId.PHYSICAL_PENETRATION),
        ("spell_penetration", StatId.SPELL_PENETRATION),
        ("weapon_critical", StatId.WEAPON_CRITICAL),
        ("spell_critical", StatId.SPELL_CRITICAL),
        ("critical_chance", StatId.CRITICAL_CHANCE),
        ("critical_damage", StatId.CRITICAL_DAMAGE),
        ("critical_resistance", StatId.CRITICAL_RESISTANCE),
        ("healing_taken", StatId.HEALING_TAKEN),
    ],
)
def test_deterministic_engine_stats_share_effect_mapping(effect_type, expected):
    effect = EffectMapper.create_additive(
        effect_type=f"  {effect_type.upper()}  ",
        value=100,
        unit=" FLAT ",
        source="Test",
    )

    assert effect.stat == expected
    assert effect.unit == EffectUnit.FLAT


def test_unknown_effect_type_fails():
    with pytest.raises(ValueError, match="Unsupported engine stat effect type"):
        EffectMapper.create_additive(
            effect_type="something_we_have_not_defined",
            value=10,
            unit="flat",
            source="Test",
        )



def test_combined_weapon_spell_damage_fans_out_to_both_engine_stats():
    effects = EffectMapper.create_additives(
        effect_type="weapon_spell_damage",
        value=174,
        unit="flat",
        source="Glyph of Increase Magical Harm",
    )

    assert [effect.stat for effect in effects] == [
        StatId.WEAPON_DAMAGE,
        StatId.SPELL_DAMAGE,
    ]
    assert all(effect.value == 174 for effect in effects)
    assert all(effect.source == "Glyph of Increase Magical Harm" for effect in effects)


def test_combined_effect_cannot_be_forced_through_singular_mapper():
    with pytest.raises(ValueError, match="maps to multiple stats"):
        EffectMapper.create_additive(
            effect_type="weapon_spell_damage",
            value=174,
            unit="flat",
            source="Glyph of Increase Magical Harm",
        )
