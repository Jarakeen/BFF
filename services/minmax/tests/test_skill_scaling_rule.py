import pytest

from services.minmax.build import Build
from services.minmax.skill_scaling import (
    get_skill_scaling_inputs,
)
from services.minmax.skill_scaling_rule import (
    SkillScalingMode,
    resolve_skill_scaling,
)
from services.minmax.stat_ids import StatId


def test_extracts_all_raw_scaling_attributes():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 24000,
            StatId.MAX_MAGICKA.value: 22000,
            StatId.MAX_STAMINA.value: 23000,
            StatId.WEAPON_DAMAGE.value: 3000,
            StatId.SPELL_DAMAGE.value: 3200,
        }
    )

    result = get_skill_scaling_inputs(build)

    assert result.max_health == 24000
    assert result.max_magicka == 22000
    assert result.max_stamina == 23000
    assert result.weapon_damage == 3000
    assert result.spell_damage == 3200


def test_missing_stats_default_to_zero():
    result = get_skill_scaling_inputs(Build())

    assert result.max_health == 0
    assert result.max_magicka == 0
    assert result.max_stamina == 0
    assert result.weapon_damage == 0
    assert result.spell_damage == 0


def test_standard_offensive_resolves_A_and_P():
    build = Build(
        base_stats={
            StatId.MAX_MAGICKA.value: 30000,
            StatId.MAX_STAMINA.value: 28000,
            StatId.WEAPON_DAMAGE.value: 6000,
            StatId.SPELL_DAMAGE.value: 6500,
        }
    )

    inputs = get_skill_scaling_inputs(build)

    result = resolve_skill_scaling(
        inputs,
        SkillScalingMode.STANDARD_OFFENSIVE,
    )

    assert result.ability == 30000
    assert result.power == 6500


def test_max_health():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 24000,
            StatId.MAX_MAGICKA.value: 22000,
        }
    )

    inputs = get_skill_scaling_inputs(build)

    result = resolve_skill_scaling(
        inputs,
        SkillScalingMode.MAX_HEALTH,
    )

    assert result.ability == 24000
    assert result.power == 0


def test_max_health_or_magicka():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 24000,
            StatId.MAX_MAGICKA.value: 26000,
        }
    )

    inputs = get_skill_scaling_inputs(build)

    result = resolve_skill_scaling(
        inputs,
        SkillScalingMode.MAX_HEALTH_OR_MAGICKA,
    )

    assert result.ability == 26000
    assert result.power == 0


def test_max_weapon_or_spell_damage():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 3000,
            StatId.SPELL_DAMAGE.value: 3400,
        }
    )

    inputs = get_skill_scaling_inputs(build)

    result = resolve_skill_scaling(
        inputs,
        SkillScalingMode.MAX_WEAPON_OR_SPELL_DAMAGE,
    )

    assert result.ability == 0
    assert result.power == 3400