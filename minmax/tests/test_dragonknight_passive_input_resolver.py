from __future__ import annotations

import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.core_stat_calculator import CoreStatCalculator
from minmax.character_progression import CharacterProgression
from minmax.dragonknight_passive_input_resolver import DragonknightPassiveInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


def _healing_taken(result: GearCalculationInputs) -> float:
    base = BaseCharacterCalculator().calculate()
    core = CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=base,
        inputs=result.core,
    )
    return float(core.derived[StatId.HEALING_TAKEN].final_value)


def test_rank_two_soul_ablaze_adds_eight_percent_healing_taken() -> None:
    result = DragonknightPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Dragonknight"),
        soul_ablaze_rank=2,
    )

    contribution = result.core.healing_taken.flat[-1]
    assert contribution.label == "Dragonknight: A Soul Ablaze"
    assert contribution.value == pytest.approx(0.08)
    assert _healing_taken(result) == pytest.approx(0.08)
    assert result.applied_effect_count == 1


def test_rank_one_soul_ablaze_adds_four_percent_healing_taken() -> None:
    result = DragonknightPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Dragonknight"),
        soul_ablaze_rank=1,
    )

    assert result.core.healing_taken.flat[-1].value == pytest.approx(0.04)
    assert _healing_taken(result) == pytest.approx(0.04)


def test_unpurchased_soul_ablaze_does_not_apply() -> None:
    result = DragonknightPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Dragonknight"),
        soul_ablaze_rank=0,
    )

    assert result.core.healing_taken.flat == ()
    assert result.applied_effect_count == 0


def test_explicit_route_without_ardent_flame_removes_soul_ablaze() -> None:
    result = DragonknightPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Dragonknight",
            ClassSkillLines=["Draconic Power", "Earthen Heart", "Restoring Light"],
        ),
        soul_ablaze_rank=2,
    )

    assert result.core.healing_taken.flat == ()


def test_foreign_class_can_gain_soul_ablaze_only_through_explicit_ardent_flame_route() -> None:
    resolver = DragonknightPassiveInputResolver()
    without_line = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Warden"),
        soul_ablaze_rank=2,
    )
    with_line = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Ardent Flame"],
        ),
        soul_ablaze_rank=2,
    )

    assert without_line.core.healing_taken.flat == ()
    assert with_line.core.healing_taken.flat[-1].value == pytest.approx(0.08)


def test_unknown_positive_rank_fails_closed_without_inventing_value() -> None:
    result = DragonknightPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Dragonknight"),
        soul_ablaze_rank=3,
    )

    assert result.core.healing_taken.flat == ()
    assert result.unresolved == ("Unsupported A Soul Ablaze rank: 3",)
