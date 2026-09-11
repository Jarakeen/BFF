from dataclasses import replace
from types import SimpleNamespace

import pytest

from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.undaunted_passive_input_resolver import UndauntedPassiveInputResolver
from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphPieceChoice,
    ExtremeArmorResourceTraitGlyphState,
)
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightState,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphState,
)
from services.extreme_named_gear_resource_armor_canonical_stat_evaluator import (
    ExtremeNamedGearResourceArmorCanonicalStatEvaluator,
)


class _ClassProgressionService:
    def normalize(self, progression, route):
        return progression


class _UndauntedProgressionService:
    def normalize(self, progression, route):
        passive_ranks = dict(progression.passive_ranks or {})
        passive_ranks["Undaunted Mettle"] = 2
        return replace(
            progression,
            owned_skill_lines=tuple((*progression.owned_skill_lines, "Undaunted")),
            passive_ranks=passive_ranks,
        )


class _Optimizer:
    def objective(self, key):
        return SimpleNamespace(key=key)

    def _evaluate(self, build, *, progression, **kwargs):
        mettle_owned = bool(
            progression.owns_skill_line("Undaunted")
            and progression.passive_rank("Undaunted Mettle") == 2
        )
        inputs = UndauntedPassiveInputResolver().apply(
            GearCalculationInputs(),
            build,
            undaunted_mettle_owned=mettle_owned,
        )
        percent = sum(
            row.value
            for row in inputs.health.skill_percent_contributions
            if row.label == "Undaunted: Undaunted Mettle"
        )
        return 10_000.0 * (1.0 + percent), ()


class _NamedGearEvaluator:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_service = _ClassProgressionService()

    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        return 10_000.0, {"build": PlayerBuild().to_dict()}, ()


def _candidate():
    return SimpleNamespace(
        attributes=SimpleNamespace(health=64, magicka=0, stamina=0),
        class_route=SimpleNamespace(),
        active_bar="front",
        identity=("Nord", "Dragonknight", (), 64, 0, 0, "front"),
    )


def _state(armor_type_count: int) -> ExtremeArmorResourceWeightTraitGlyphState:
    if armor_type_count == 1:
        weights = tuple((slot, "Light") for slot in ARMOR_SLOTS)
    elif armor_type_count == 2:
        weights = tuple(
            (slot, "Medium" if index == 0 else "Light")
            for index, slot in enumerate(ARMOR_SLOTS)
        )
    elif armor_type_count == 3:
        weights = tuple(
            (
                slot,
                "Heavy" if index == 0 else ("Medium" if index == 1 else "Light"),
            )
            for index, slot in enumerate(ARMOR_SLOTS)
        )
    else:
        raise ValueError(armor_type_count)

    trait_glyph = ExtremeArmorResourceTraitGlyphState(
        objective_key="max_health",
        pieces=tuple(
            ExtremeArmorResourceTraitGlyphPieceChoice(
                slot=slot,
                trait="Divines",
                enchant="",
                direct_delta=0.0,
            )
            for slot in ARMOR_SLOTS
        ),
        direct_glyph_delta=0.0,
    )
    return ExtremeArmorResourceWeightTraitGlyphState(
        objective_key="max_health",
        weight_state=ExtremeArmorResourceWeightState(
            objective_key="max_health",
            weights=weights,
        ),
        trait_glyph_state=trait_glyph,
    )


@pytest.mark.parametrize(
    ("armor_type_count", "expected"),
    ((1, 10_200.0), (2, 10_400.0), (3, 10_600.0)),
)
def test_resource_armor_canonical_scoring_applies_mettle_by_distinct_weight_count(
    armor_type_count,
    expected,
):
    evaluator = ExtremeNamedGearResourceArmorCanonicalStatEvaluator(
        evaluator=_NamedGearEvaluator(),
        armor_state=_state(armor_type_count),
        undaunted_progression_service=_UndauntedProgressionService(),
    )

    value, payload, unresolved = evaluator.evaluate_candidate(
        "max_health",
        _candidate(),
    )

    assert value == pytest.approx(expected)
    assert payload["armor_type_count"] == armor_type_count
    assert payload["undaunted_mettle_rank"] == 2
    assert payload["undaunted_mettle_progression_applied"] is True
    assert unresolved == ()
