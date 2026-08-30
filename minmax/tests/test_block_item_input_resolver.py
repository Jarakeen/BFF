import pytest

from minmax.block_item_input_resolver import BlockItemInputResolver
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.core_stat_calculator import CoreStatCalculator
from minmax.base_character_state import BaseCharacterCalculator
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


class EmptyGearSetRepository:
    def get_set(self, name):
        return None

    def get_set_by_id(self, set_id):
        return None

    def get_bonuses(self, set_id):
        return []


def _state(inputs):
    return CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=inputs.core,
    )


def test_gold_cp160_sturdy_is_four_percent_sequential_block_cost_reduction():
    build = PlayerBuild()
    build.Armor["Chest"].update({"Trait": "Sturdy", "Quality": "Gold", "Level": "CP160"})

    resolved = BlockItemInputResolver().apply(GearCalculationInputs(), build)

    modifier = resolved.core.block_cost.sequential_modifiers[-1]
    assert modifier.label == "Chest: Sturdy"
    assert modifier.percent == pytest.approx(-0.04)
    assert _state(resolved).derived[StatId.BLOCK_COST].final_value == 1680
    assert resolved.applied_effect_count == 1
    assert resolved.unresolved == ()


def test_truly_superb_bracing_is_flat_reduction_before_percent_modifiers():
    build = PlayerBuild(
        Ring1=GearSlot(
            Enchant="Block Cost",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )

    resolved = BlockItemInputResolver().apply(GearCalculationInputs(), build)

    assert resolved.core.block_cost.flat_reductions[-1] == (
        "Ring 1: Glyph of Bracing",
        pytest.approx(203.0),
    )
    assert _state(resolved).derived[StatId.BLOCK_COST].final_value == 1547


def test_gold_infused_jewelry_scales_bracing_before_block_cost_calculation():
    build = PlayerBuild(
        Ring1=GearSlot(
            Trait="Infused",
            Quality="Gold",
            Enchant="Block Cost",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )

    resolved = BlockItemInputResolver().apply(GearCalculationInputs(), build)

    label, reduction = resolved.core.block_cost.flat_reductions[-1]
    assert label == "Ring 1: Glyph of Bracing (Infused +60%)"
    assert reduction == pytest.approx(203.0 * 1.60)
    assert _state(resolved).derived[StatId.BLOCK_COST].final_value == 1426


def test_bracing_flat_reduction_precedes_sturdy_percentage_reduction():
    build = PlayerBuild(
        Ring1=GearSlot(
            Trait="Infused",
            Quality="Gold",
            Enchant="Block Cost",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    build.Armor["Chest"].update({"Trait": "Sturdy", "Quality": "Gold", "Level": "CP160"})

    resolved = BlockItemInputResolver().apply(GearCalculationInputs(), build)
    trace = _state(resolved).derived[StatId.BLOCK_COST]

    assert trace.final_value == 1369
    assert trace.steps[1][0] == "Ring 1: Glyph of Bracing (Infused +60%)"
    assert trace.steps[1][1] == "subtract"
    assert trace.steps[2][0] == "Chest: Sturdy"
    assert trace.steps[2][1] == "multiply"


def test_successful_bracing_resolution_removes_only_matching_generic_unresolved_message():
    build = PlayerBuild(
        Ring1=GearSlot(
            Enchant="Block Cost",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    original = GearCalculationInputs(
        unresolved=(
            "Ring 1 enchant not yet resolved: Block Cost",
            "Potion selected but potion effects are not yet modeled: test",
        )
    )

    resolved = BlockItemInputResolver().apply(original, build)

    assert "Ring 1 enchant not yet resolved: Block Cost" not in resolved.unresolved
    assert "Potion selected but potion effects are not yet modeled: test" in resolved.unresolved


def test_context_factory_applies_sturdy_and_bracing_without_passive_ownership():
    build = PlayerBuild(
        Ring1=GearSlot(
            Enchant="Block Cost",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    build.Armor["Chest"].update({"Trait": "Sturdy", "Quality": "Gold", "Level": "CP160"})

    context = BuildCalculationContextFactory(
        gear_set_repository=EmptyGearSetRepository(),
    ).build(
        character_id="character",
        build_id="block-items",
        build=build,
        progression=CharacterProgression(),
    )

    assert context.core_state.derived[StatId.BLOCK_COST].final_value == 1486
    assert context.gear_effects_applied == 2
    assert not context.unresolved_gear_effects


def test_sturdy_without_verified_cp160_level_stays_unresolved():
    build = PlayerBuild()
    build.Armor["Chest"].update({"Trait": "Sturdy", "Quality": "Gold", "Level": "1"})

    resolved = BlockItemInputResolver().apply(GearCalculationInputs(), build)

    assert resolved.core.block_cost.sequential_modifiers == ()
    assert any("Chest Sturdy: needs verified CP160 trait scaling" in message for message in resolved.unresolved)
