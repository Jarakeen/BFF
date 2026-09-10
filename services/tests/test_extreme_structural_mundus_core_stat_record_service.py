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
from services.extreme_structural_mundus_core_stat_record_service import (
    ExtremeBestMundusStructuralStatEvaluator,
    ExtremeStructuralMundusCoreStatRecordService,
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


class _MundusRepository:
    def list_names(self):
        return ["The Mage", "The Lord", "The Mage", ""]


class _CanonicalEvaluator:
    VALUES = {
        "": 100.0,
        "The Lord": 130.0,
        "The Mage": 120.0,
    }

    def evaluate_candidate(self, objective_key, candidate, *, mundus=""):
        return (
            self.VALUES[mundus],
            {"objective": objective_key, "mundus": mundus, "race": candidate.race},
            (),
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


def test_mundus_choices_include_no_mundus_and_dedupe_exact_repository_names():
    evaluator = ExtremeBestMundusStructuralStatEvaluator(
        evaluator=_CanonicalEvaluator(),
        mundus_repository=_MundusRepository(),
    )

    assert evaluator.mundus_choices() == ("", "The Mage", "The Lord")


def test_mundus_evaluator_selects_best_canonical_score_and_preserves_payload():
    evaluator = ExtremeBestMundusStructuralStatEvaluator(
        evaluator=_CanonicalEvaluator(),
        mundus_repository=_MundusRepository(),
    )

    value, payload, unresolved = evaluator("max_health", _candidate())

    assert value == 130.0
    assert payload["mundus"] == "The Lord"
    assert unresolved == ()


def test_record_closes_only_mundus_axis_and_counts_expanded_denominator():
    candidate = _candidate()
    best = ExtremeStructuralScore(
        candidate=candidate,
        value=130.0,
        payload={"mundus": "The Lord", "race": "Argonian"},
    )
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="max_health",
        best=best,
        candidates_scored=10,
        ties_at_best=1,
        structural_scope=("all races", "all routes", "all attributes", "both bars"),
        deferred_dynamic_axes=("gear and legal set/package topology", "Mundus", "potions"),
        structural_denominator_proven=True,
    )
    search = _SearchService(structural)
    mundus = ExtremeBestMundusStructuralStatEvaluator(
        evaluator=_CanonicalEvaluator(),
        mundus_repository=_MundusRepository(),
    )
    service = ExtremeStructuralMundusCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
        mundus_evaluator=mundus,
    )

    record = service.record("max_health")

    assert record.raw_value == 130.0
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.winning_build["mundus"] == "The Lord"
    assert record.search_coverage.candidates_screened == 30
    assert record.search_coverage.candidates_optimized == 30
    assert "Mundus" not in record.search_coverage.omitted
    assert record.search_coverage.omitted == (
        "gear and legal set/package topology",
        "potions",
    )
    assert any("Update-50 Mundus" in item for item in record.search_coverage.searched)
    assert record.search_coverage.denominator_proven is False
    assert search.requested == ["max_health"]


def test_record_can_be_proven_only_when_no_other_dynamic_axes_remain():
    candidate = _candidate()
    best = ExtremeStructuralScore(
        candidate=candidate,
        value=130.0,
        payload={"mundus": "The Lord"},
    )
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="max_health",
        best=best,
        candidates_scored=2,
        ties_at_best=1,
        structural_scope=("structural",),
        deferred_dynamic_axes=("Mundus",),
        structural_denominator_proven=True,
    )
    service = ExtremeStructuralMundusCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=_SearchService(structural),
        mundus_evaluator=ExtremeBestMundusStructuralStatEvaluator(
            evaluator=_CanonicalEvaluator(),
            mundus_repository=_MundusRepository(),
        ),
    )

    record = service.record("max_health")

    assert record.proof_status is ExtremeRecordProofStatus.PROVEN
    assert record.globally_proven is True
    assert record.search_coverage.candidates_screened == 6


def test_cataloged_non_core_objective_fails_closed():
    candidate = _candidate()
    structural = ExtremeStructuralGlobalSearchResult(
        objective_key="critical_heal",
        best=ExtremeStructuralScore(candidate=candidate, value=1.0, payload={}),
        candidates_scored=1,
        ties_at_best=1,
        structural_scope=("structural",),
        deferred_dynamic_axes=("Mundus",),
        structural_denominator_proven=True,
    )
    service = ExtremeStructuralMundusCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=_SearchService(structural),
        mundus_evaluator=ExtremeBestMundusStructuralStatEvaluator(
            evaluator=_CanonicalEvaluator(),
            mundus_repository=_MundusRepository(),
        ),
    )

    with pytest.raises(ValueError, match="does not support objective"):
        service.record("critical_heal")
