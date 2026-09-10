from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_progression import AttributeAllocation
from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_structural_global_search_service import (
    ExtremeStructuralCandidate,
    ExtremeStructuralGlobalSearchResult,
    ExtremeStructuralScore,
)
from services.extreme_structural_mundus_food_core_stat_record_service import (
    ExtremeBestMundusFoodStructuralStatEvaluator,
    ExtremeStructuralMundusFoodCoreStatRecordService,
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


class _CanonicalEvaluator:
    VALUES = {
        ("", ""): 100.0,
        ("The Lord", ""): 130.0,
        ("", "Longfin Pasty"): 150.0,
        ("The Lord", "Longfin Pasty"): 180.0,
        ("", "Mystery Stew"): 100.0,
        ("The Lord", "Mystery Stew"): 130.0,
    }

    def evaluate_candidate(self, objective_key, candidate, *, mundus="", food=""):
        return (
            self.VALUES[(mundus, food)],
            {
                "objective": objective_key,
                "mundus": mundus,
                "food": food,
                "race": candidate.race,
            },
            (),
        )


class _MundusRepository:
    def list_names(self):
        return ["The Lord", "The Lord", ""]


class _MundusEvaluator:
    def __init__(self):
        self.evaluator = _CanonicalEvaluator()
        self.mundus_repository = _MundusRepository()

    def mundus_choices(self):
        return ("", "The Lord")

    def evaluate_candidate(self, objective_key, candidate, *, food=""):
        best = None
        for mundus in self.mundus_choices():
            value, payload, unresolved = self.evaluator.evaluate_candidate(
                objective_key,
                candidate,
                mundus=mundus,
                food=food,
            )
            row = (value, payload, unresolved)
            if best is None or value > best[0]:
                best = row
        return best


class _ProvisioningRepository:
    def list_names(self):
        return ["Longfin Pasty", "Mystery Stew", "Longfin Pasty", ""]

    def resolve(self, name):
        if name == "Mystery Stew":
            return [], ["Food/Drink has no mapped static character-sheet stats: Mystery Stew"]
        return [object()], []


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


def _evaluator():
    return ExtremeBestMundusFoodStructuralStatEvaluator(
        mundus_evaluator=_MundusEvaluator(),
        provisioning_repository=_ProvisioningRepository(),
    )


def test_food_choices_include_no_food_and_dedupe_exact_names():
    assert _evaluator().food_choices() == ("", "Longfin Pasty", "Mystery Stew")


def test_food_evaluator_selects_best_nested_mundus_food_pair():
    value, payload, unresolved = _evaluator()("max_health", _candidate())

    assert value == 180.0
    assert payload["mundus"] == "The Lord"
    assert payload["food"] == "Longfin Pasty"
    assert "Mystery Stew" in " ".join(unresolved)


def test_unmapped_food_remains_visible_even_when_it_does_not_win():
    _, _, unresolved = _evaluator()("max_health", _candidate())

    assert unresolved == (
        "Food/Drink has no mapped static character-sheet stats: Mystery Stew",
    )


def test_record_closes_mundus_and_food_axes_but_preserves_remaining_omissions():
    candidate = _candidate()
    best = ExtremeStructuralScore(
        candidate=candidate,
        value=180.0,
        payload={"mundus": "The Lord", "food": "Longfin Pasty"},
    )
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="max_health",
        best=best,
        candidates_scored=10,
        ties_at_best=1,
        structural_scope=("all races", "all routes", "all attributes", "both bars"),
        deferred_dynamic_axes=(
            "gear and legal set/package topology",
            "Mundus",
            "food/drink",
            "potions",
        ),
        structural_denominator_proven=True,
        unresolved=("Food/Drink has no mapped static character-sheet stats: Mystery Stew",),
    )
    search = _SearchService(structural)
    service = ExtremeStructuralMundusFoodCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
        evaluator=_evaluator(),
    )

    record = service.record("max_health")

    assert record.raw_value == 180.0
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.winning_build["mundus"] == "The Lord"
    assert record.winning_build["food"] == "Longfin Pasty"
    assert record.search_coverage.candidates_screened == 60
    assert record.search_coverage.candidates_optimized == 60
    assert record.search_coverage.omitted == (
        "gear and legal set/package topology",
        "potions",
    )
    assert "Mundus" not in record.search_coverage.omitted
    assert "food/drink" not in record.search_coverage.omitted
    assert any("food/drink" in item for item in record.search_coverage.searched)
    assert record.unresolved == (
        "Food/Drink has no mapped static character-sheet stats: Mystery Stew",
    )
    assert search.requested == ["max_health"]


def test_cataloged_non_core_objective_fails_closed():
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="critical_heal",
        best=ExtremeStructuralScore(candidate=_candidate(), value=1.0, payload={}),
        candidates_scored=1,
        ties_at_best=1,
        structural_scope=("structural",),
        deferred_dynamic_axes=("Mundus", "food/drink"),
        structural_denominator_proven=True,
    )
    service = ExtremeStructuralMundusFoodCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=_SearchService(structural),
        evaluator=_evaluator(),
    )

    with pytest.raises(ValueError, match="does not support objective"):
        service.record("critical_heal")
