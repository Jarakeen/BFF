from __future__ import annotations

import pytest

from minmax.base_character_state import BaseCharacterCalculator
from minmax.character_progression import CharacterProgression
from minmax.core_stat_calculator import CoreStatCalculator
from minmax.derived_stats import StatContribution
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.static_build_inputs import StaticBuildInputResolver
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class _RitualRepository:
    def get_effects(self, name: str, *, multiplier: float = 1.0):
        assert name == "The Ritual"
        return (
            [
                Effect(
                    source="Mundus: The Ritual",
                    stat=StatId.HEALING_DONE,
                    operation=EffectOperation.ADD_PERCENT,
                    value=8.0 * multiplier,
                    unit=EffectUnit.PERCENT,
                )
            ],
            [],
        )


def _six_divines_one_infused_ritual_build() -> PlayerBuild:
    build = PlayerBuild(Mundus="The Ritual")
    for slot in ("Head", "Chest", "Hands", "Waist", "Legs", "Feet"):
        build.Armor[slot]["Trait"] = "Divines"
        build.Armor[slot]["Quality"] = "Gold"
    build.Armor["Shoulders"]["Trait"] = "Infused"
    build.Armor["Shoulders"]["Quality"] = "Gold"
    return build


def test_six_divines_infused_shoulders_and_powered_match_live_healing_sheet():
    build = _six_divines_one_infused_ritual_build()
    initial = GearCalculationInputs()
    initial = GearCalculationInputs(
        core=initial.core.__class__(
            **{
                **initial.core.__dict__,
                "healing_done": initial.core.healing_done.__class__(
                    additive_after_percent=(
                        StatContribution("Front Bar: Powered", 0.09),
                        StatContribution("Champion Point: Blessed", 0.02),
                    )
                ),
            }
        )
    )

    resolved = StaticBuildInputResolver(mundus_repository=_RitualRepository()).apply(
        initial,
        build,
        active_bar="front",
    )

    ritual = resolved.core.healing_done.additive_after_percent[-1]
    assert ritual.label == "Mundus: The Ritual"
    assert ritual.value == pytest.approx(0.12368)

    state = CoreStatCalculator().calculate(
        character_progression=CharacterProgression(),
        base_character=BaseCharacterCalculator().calculate(),
        inputs=resolved.core,
    )

    assert state.derived[StatId.HEALING_DONE].final_value == pytest.approx(0.23368)
