from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation
from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_structural_global_search_service import (
    ExtremeStructuralCandidate,
    ExtremeStructuralGlobalSearchResult,
    ExtremeStructuralScore,
)
from services.extreme_structural_mundus_food_potion_core_stat_record_service import (
    ExtremeBestMundusFoodPotionStructuralStatEvaluator,
    ExtremeStructuralMundusFoodPotionCoreStatRecordService,
)


@dataclass(frozen=True)
class _BaseClass:
    value: str = "warden"


@dataclass(frozen=True)
class _Route:
    base_class: _BaseClass = _BaseClass()
    equipped_skill_lines: tuple[str, ...] = (
        "green_balance",
        "animal_companions",
        "winters_embrace",
    )


class _MundusEvaluator:
    def mundus_choices(self):
        return ("", "The Lord")


class _FoodEvaluator:
    def __init__(self):
        self.mundus_evaluator = _MundusEvaluator()
        self.calls = []

    def food_choices(self):
        return ("", "Longfin Pasty")

    def evaluate_candidate(self, objective_key, candidate, *, potion="", active_buffs=()):
        self.calls.append((potion, tuple(active_buffs)))
        bonus = {
            "": 0.0,
            "alchemy_formula:u50:health:restore_health": 25.0,
            "alchemy_formula:u50:spell:increase_spell_power+spell_critical": 60.0,
        }[potion]
        payload = {
            "objective": objective_key,
            "race": candidate.race,
            "mundus": "The Lord",
            "food": "Longfin Pasty",
            "potion": potion,
            "active_buffs": tuple(active_buffs),
        }
        return 100.0 + bonus, payload, ()


class _PotionRepository:
    def __init__(self, *, catalog_unresolved=()):
        self.catalog_unresolved = tuple(catalog_unresolved)
        self.formulas = (
            SimpleNamespace(canonical_id="alchemy_formula:u50:health:restore_health"),
            SimpleNamespace(
                canonical_id="alchemy_formula:u50:spell:increase_spell_power+spell_critical"
            ),
        )

    def catalog(self):
        return SimpleNamespace(formulas=self.formulas, unresolved=self.catalog_unresolved)

    def resolve(self, selection):
        if selection.endswith("restore_health"):
            return SimpleNamespace(
                canonical_traits=("Restore Health",),
                unresolved=(),
            )
        return SimpleNamespace(
            canonical_traits=("Increase Spell Power", "Spell Critical"),
            unresolved=(),
        )


class _Optimizer:
    database_path = "unused.db"


class _SearchService:
    def __init__(self, result):
        self.result = result
        self.requested = []

    def search(self, objective_key):
        self.requested.append(objective_key)
        return self.result


def _candidate():
    return ExtremeStructuralCandidate(
        race="Argonian",
        class_route=_Route(),
        attributes=AttributeAllocation(health=64, magicka=0, stamina=0),
        active_bar="front",
    )


def _evaluator(*, catalog_unresolved=(), base_active_buffs=()):
    return ExtremeBestMundusFoodPotionStructuralStatEvaluator(
        food_evaluator=_FoodEvaluator(),
        potion_repository=_PotionRepository(catalog_unresolved=catalog_unresolved),
        base_active_buffs=base_active_buffs,
    )


def test_potion_states_include_empty_baseline_and_map_u50_named_buffs():
    evaluator = _evaluator()

    states = evaluator.potion_states()

    assert tuple(state.selection for state in states) == (
        "",
        "alchemy_formula:u50:health:restore_health",
        "alchemy_formula:u50:spell:increase_spell_power+spell_critical",
    )
    assert states[1].active_buffs == ("Major Fortitude",)
    assert states[2].active_buffs == ("Major Sorcery", "Major Prophecy")
    assert evaluator.denominator_proven is True


def test_potion_evaluator_selects_best_active_formula_and_preserves_runtime_payload():
    evaluator = _evaluator()

    value, payload, unresolved = evaluator("spell_damage", _candidate())

    assert value == 160.0
    assert payload["potion"] == "alchemy_formula:u50:spell:increase_spell_power+spell_critical"
    assert payload["active_buffs"] == ("Major Sorcery", "Major Prophecy")
    assert unresolved == ()


def test_fixed_transient_state_is_composed_with_every_potion_snapshot():
    marker = "__emperor_home_keeps__:6"
    evaluator = _evaluator(base_active_buffs=(marker,))

    _, payload, unresolved = evaluator("max_health", _candidate())

    assert unresolved == ()
    assert payload["active_buffs"] == (marker, "Major Sorcery", "Major Prophecy")
    assert evaluator.food_evaluator.calls[0][1] == (marker,)
    assert all(marker in buffs for _, buffs in evaluator.food_evaluator.calls)


def test_catalog_unresolved_evidence_prevents_potion_denominator_proof():
    evaluator = _evaluator(catalog_unresolved=("one formula row was rejected",))

    evaluator.potion_states()

    assert evaluator.denominator_proven is False
    assert evaluator.unresolved == ("one formula row was rejected",)


def test_record_closes_potion_axis_and_counts_full_nested_denominator():
    evaluator = _evaluator()
    best = ExtremeStructuralScore(
        candidate=_candidate(),
        value=160.0,
        payload={
            "mundus": "The Lord",
            "food": "Longfin Pasty",
            "potion": "alchemy_formula:u50:spell:increase_spell_power+spell_critical",
            "active_buffs": ("Major Sorcery", "Major Prophecy"),
        },
    )
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="spell_damage",
        best=best,
        candidates_scored=10,
        ties_at_best=1,
        structural_scope=("all races", "all routes", "all attributes", "both bars"),
        deferred_dynamic_axes=(
            "gear and legal set/package topology",
            "Mundus",
            "food/drink",
            "potions",
            "Champion Points",
        ),
        structural_denominator_proven=True,
    )
    search = _SearchService(structural)
    service = ExtremeStructuralMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
        evaluator=evaluator,
    )

    record = service.record("spell_damage")

    # 10 structural × 2 Mundus × 2 food × 3 potion states.
    assert record.search_coverage.candidates_screened == 120
    assert record.search_coverage.candidates_optimized == 120
    assert record.search_coverage.omitted == (
        "gear and legal set/package topology",
        "Champion Points",
    )
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.winning_build["potion"].startswith("alchemy_formula:u50:")
    assert record.self_provided_conditions == ("Major Sorcery", "Major Prophecy")
    assert record.runtime_prerequisites == (
        "Winning potion formula must be activated and its mapped effects active at the scored snapshot.",
    )
    assert any("potion formula" in item for item in record.search_coverage.searched)
    assert search.requested == ["spell_damage"]


def test_cataloged_non_core_objective_fails_closed():
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="critical_heal",
        best=ExtremeStructuralScore(candidate=_candidate(), value=1.0, payload={}),
        candidates_scored=1,
        ties_at_best=1,
        structural_scope=("structural",),
        deferred_dynamic_axes=("Mundus", "food/drink", "potions"),
        structural_denominator_proven=True,
    )
    service = ExtremeStructuralMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=_SearchService(structural),
        evaluator=_evaluator(),
    )

    with pytest.raises(ValueError, match="does not support"):
        service.record("critical_heal")
