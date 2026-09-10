from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_structural_core_stat_record_service import (
    ExtremeCanonicalStructuralStatEvaluator,
    ExtremeStructuralCoreStatRecordService,
)
from services.extreme_structural_global_search_service import (
    ExtremeStructuralCandidate,
    ExtremeStructuralGlobalSearchResult,
    ExtremeStructuralScore,
)


def _route() -> ExtremeHealClassRoute:
    return ExtremeHealClassRoute(
        base_class=CharacterClass.WARDEN,
        configuration=ClassSkillLineConfiguration(
            equipped_skill_lines=(
                "animal_companions",
                "green_balance",
                "winters_embrace",
            )
        ),
    )


@dataclass(frozen=True)
class _Objective:
    key: str
    label: str


class _Optimizer:
    database_path = "unused.db"

    @staticmethod
    def objective(key):
        return _Objective(key=key, label="Maximum Health")

    def _evaluate(self, build, *, progression, character_id, build_id, objective, active_bar):
        assert build.Race == "Argonian"
        assert build.EsoClass == "warden"
        assert build.ClassSkillLines == [
            "animal_companions",
            "green_balance",
            "winters_embrace",
        ]
        assert build.AttributeHealth == 64
        assert progression.attributes.health == 64
        assert active_bar == "front"
        assert character_id == "extreme-structural-global"
        assert objective.key == "max_health"
        return 54321.0, ("one diagnostic",)


class _ProgressionService:
    def normalize(self, progression, route):
        assert isinstance(progression, CharacterProgression)
        assert route == _route()
        return progression


def test_canonical_structural_evaluator_materializes_candidate_and_uses_shared_optimizer():
    evaluator = ExtremeCanonicalStructuralStatEvaluator(
        optimizer=_Optimizer(),
        progression_service=_ProgressionService(),
    )
    candidate = ExtremeStructuralCandidate(
        race="Argonian",
        class_route=_route(),
        attributes=AttributeAllocation(health=64, magicka=0, stamina=0),
        active_bar="front",
    )

    value, payload, unresolved = evaluator("max_health", candidate)

    assert value == 54321.0
    assert unresolved == ("one diagnostic",)
    assert payload["race"] == "Argonian"
    assert payload["base_class"] == "warden"
    assert payload["attributes"] == {"health": 64, "magicka": 0, "stamina": 0}
    assert payload["active_bar"] == "front"
    assert isinstance(payload["build"], dict)


class _SearchService:
    def __init__(self, result):
        self.result = result
        self.seen = []

    def search(self, key):
        self.seen.append(key)
        return self.result


def _search_result(*, deferred=("gear",), unresolved=()):
    candidate = ExtremeStructuralCandidate(
        race="Argonian",
        class_route=_route(),
        attributes=AttributeAllocation(health=64, magicka=0, stamina=0),
        active_bar="front",
    )
    return ExtremeStructuralGlobalSearchResult(
        objective_key="max_health",
        best=ExtremeStructuralScore(
            candidate=candidate,
            value=54321.0,
            payload={"build": {"BuildName": "winner"}},
        ),
        candidates_scored=1234,
        ties_at_best=2,
        structural_scope=("races", "routes", "attributes", "bars"),
        deferred_dynamic_axes=tuple(deferred),
        structural_denominator_proven=True,
        unresolved=tuple(unresolved),
    )


def test_record_wraps_structural_winner_as_lower_bound_while_dynamic_axes_remain():
    search = _SearchService(_search_result())
    service = ExtremeStructuralCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
    )

    record = service.record("max_health")

    assert search.seen == ["max_health"]
    assert record.objective_key == "max_health"
    assert record.raw_value == 54321.0
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.globally_proven is False
    assert record.search_coverage.candidates_screened == 1234
    assert record.search_coverage.omitted == ("gear",)
    assert record.winning_build == {"build": {"BuildName": "winner"}}
    assert "2 tied" in record.explanation[1]


def test_record_can_promote_only_when_entire_dynamic_denominator_is_also_closed():
    search = _SearchService(_search_result(deferred=()))
    service = ExtremeStructuralCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
    )

    record = service.record("max_health")

    assert record.proof_status is ExtremeRecordProofStatus.PROVEN
    assert record.globally_proven is True
    assert record.search_coverage.denominator_proven is True


def test_unresolved_search_evidence_blocks_proven_status_even_with_closed_denominator():
    search = _SearchService(_search_result(deferred=(), unresolved=("missing passive proof",)))
    service = ExtremeStructuralCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
    )

    record = service.record("max_health")

    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.globally_proven is False
    assert record.unresolved == ("missing passive proof",)


def test_missing_structural_winner_returns_unresolved_record():
    search = _SearchService(
        ExtremeStructuralGlobalSearchResult(
            objective_key="max_health",
            best=None,
            candidates_scored=0,
            ties_at_best=0,
            structural_scope=("races",),
            deferred_dynamic_axes=("gear",),
            structural_denominator_proven=False,
            unresolved=(),
        )
    )
    service = ExtremeStructuralCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
    )

    record = service.record("max_health")

    assert record.raw_value is None
    assert record.proof_status is ExtremeRecordProofStatus.UNRESOLVED
    assert "no scored candidate" in record.unresolved[0]


def test_non_core_record_objective_fails_closed_before_search():
    search = _SearchService(_search_result())
    service = ExtremeStructuralCoreStatRecordService(
        optimizer=_Optimizer(),
        search_service=search,
    )

    with pytest.raises(ValueError, match="does not support"):
        service.record("critical_heal")

    assert search.seen == []
