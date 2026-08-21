from services.minmax.build import Build
from services.minmax.stat_ids import StatId
from services.minmax.skill_scaling import (
    get_skill_scaling_inputs,
)


def test_extracts_raw_scaling_stats():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 35000,
            StatId.MAX_MAGICKA.value: 30000,
            StatId.MAX_STAMINA.value: 28000,
            StatId.WEAPON_DAMAGE.value: 6000,
            StatId.SPELL_DAMAGE.value: 6500,
        }
    )

    result = get_skill_scaling_inputs(build)

    assert result.max_health == 35000
    assert result.max_magicka == 30000
    assert result.max_stamina == 28000
    assert result.weapon_damage == 6000
    assert result.spell_damage == 6500


def test_missing_stats_default_to_zero():
    result = get_skill_scaling_inputs(Build())

    assert result.max_health == 0
    assert result.max_magicka == 0
    assert result.max_stamina == 0
    assert result.weapon_damage == 0
    assert result.spell_damage == 0