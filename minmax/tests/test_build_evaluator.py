from pathlib import Path

from minmax.build import Build
from minmax.build_evaluation import BuildEvaluation
from minmax.build_evaluator import BuildEvaluator
from minmax.effects import (
    Effect,
    EffectOperation,
)
from minmax.rule_repository import RuleRepository
from minmax.stat_ids import StatId
from minmax.weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)
from minmax.weapon_enchantment_repository import (
    WeaponEnchantmentRepository,
)


def test_empty_build_evaluates():
    result = BuildEvaluator().evaluate(Build())

    assert isinstance(result, BuildEvaluation)
    assert result.combat_effects == ()
    assert result.combat_contributions == ()
    assert result.total_damage_contribution == 0
    assert result.total_healing_contribution == 0


def test_base_stats_are_evaluated():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 1000,
        }
    )

    result = BuildEvaluator().evaluate(build)

    assert result.stats.value(
        StatId.WEAPON_DAMAGE
    ) == 1000


def test_stat_effect_is_evaluated():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 1000,
        }
    )

    build.add_effect(
        Effect(
            operation=EffectOperation.ADD,
            value=500,
            source="Weapon Damage",
            stat=StatId.WEAPON_DAMAGE,
        )
    )

    result = BuildEvaluator().evaluate(build)

    assert result.stats.value(
        StatId.WEAPON_DAMAGE
    ) == 1500


def test_stat_effect_is_not_added_to_combat_results():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 1000,
        }
    )

    build.add_effect(
        Effect(
            operation=EffectOperation.ADD,
            value=500,
            source="Weapon Damage",
            stat=StatId.WEAPON_DAMAGE,
        )
    )

    result = BuildEvaluator().evaluate(build)

    assert result.stats.value(
        StatId.WEAPON_DAMAGE
    ) == 1500

    assert result.combat_effects == ()
    assert result.combat_contributions == ()


DB_PATH = Path("data/eso.db")
FROST_ENCHANTMENT_ID = 5365


def test_weapon_enchantment_is_evaluated():
    enchantment_repository = WeaponEnchantmentRepository(
        DB_PATH
    )

    rule_repository = RuleRepository(
        DB_PATH
    )

    weapon_service = WeaponEnchantmentEffectService(
        enchantment_repository=enchantment_repository,
        rule_repository=rule_repository,
    )

    evaluator = BuildEvaluator(
        weapon_enchantment_service=weapon_service,
    )

    build = Build()

    build.add_weapon(
        enchantment_item_id=FROST_ENCHANTMENT_ID,
    )

    result = evaluator.evaluate(build)

    assert len(result.combat_effects) == 1

    effect = result.combat_effects[0]

    assert effect.effect_type == "damage"
    assert effect.value == 2534
    assert effect.damage_type == "frost"

    assert len(result.combat_contributions) == 1

    contribution = result.combat_contributions[0]

    assert contribution.raw_value == 2534
    assert contribution.effective_value == 2534
    assert contribution.uptime == 1.0

    assert result.total_damage_contribution == 2534