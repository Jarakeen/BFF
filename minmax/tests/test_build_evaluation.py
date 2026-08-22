from pathlib import Path

from minmax.build import Build
from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)
from minmax.weapon_enchantment_repository import (
    WeaponEnchantmentRepository,
)
from minmax.build_evaluation import BuildEvaluation
from minmax.calculation import CalculationResult
from minmax.combat_calculation import CombatEffectResult
from minmax.combat_contribution import CombatContribution
from minmax.build_evaluator import BuildEvaluator
DB_PATH = Path("data/eso.db")

def weapon_enchantment_service():
    return WeaponEnchantmentEffectService(
        enchantment_repository=WeaponEnchantmentRepository(DB_PATH),
        rule_repository=RuleRepository(DB_PATH),
    )

def test_empty_build_evaluation():
    evaluation = BuildEvaluation(
        stats=CalculationResult(stats={}),
        combat_effects=(),
        combat_contributions=(),
    )

    assert evaluation.stats.stats == {}
    assert evaluation.combat_effects == ()
    assert evaluation.combat_contributions == ()
    assert evaluation.total_damage_contribution == 0
    assert evaluation.total_healing_contribution == 0


def test_damage_contribution_is_summed():
    evaluation = BuildEvaluation(
        stats=CalculationResult(stats={}),
        combat_effects=(),
        combat_contributions=(
            CombatContribution(
                source="Frost Enchantment",
                effect_type="damage",
                raw_value=2534,
                uptime=1.0,
                effective_value=2534,
            ),
            CombatContribution(
                source="Fire Enchantment",
                effect_type="damage",
                raw_value=1900,
                uptime=0.5,
                effective_value=950,
            ),
        ),
    )

    assert evaluation.total_damage_contribution == 3484


def test_healing_contribution_is_summed():
    evaluation = BuildEvaluation(
        stats=CalculationResult(stats={}),
        combat_effects=(),
        combat_contributions=(
            CombatContribution(
                source="Absorb Health",
                effect_type="health_restore",
                raw_value=861,
                uptime=1.0,
                effective_value=861,
            ),
            CombatContribution(
                source="Healing Effect",
                effect_type="health_restore",
                raw_value=500,
                uptime=0.5,
                effective_value=250,
            ),
        ),
    )

    assert evaluation.total_healing_contribution == 1111


def test_damage_and_healing_are_separated():
    evaluation = BuildEvaluation(
        stats=CalculationResult(stats={}),
        combat_effects=(),
        combat_contributions=(
            CombatContribution(
                source="Damage",
                effect_type="damage",
                raw_value=1000,
                uptime=1.0,
                effective_value=1000,
            ),
            CombatContribution(
                source="Healing",
                effect_type="health_restore",
                raw_value=500,
                uptime=1.0,
                effective_value=500,
            ),
        ),
    )

    assert evaluation.total_damage_contribution == 1000
    assert evaluation.total_healing_contribution == 500
    
def test_build_evaluation_resolves_weapon_enchantment():
    build = Build(name="Frost Enchanted Staff")

    build.add_weapon(
        enchantment_item_id=5365,
        trait="infused",
        quality="legendary",
    )

    evaluator = BuildEvaluator(
        weapon_enchantment_service=weapon_enchantment_service(),
    )

    result = evaluator.evaluate(build)

    assert len(result.combat_effects) == 1
    assert len(result.combat_contributions) == 1

    effect = result.combat_effects[0]
    contribution = result.combat_contributions[0]

    assert effect.effect_type == "damage"
    assert effect.damage_type == "frost"

    assert contribution.effect_type == "damage"
    assert contribution.effective_value > 0
    assert contribution.source == "Glyph of Frost"    