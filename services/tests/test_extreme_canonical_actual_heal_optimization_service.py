from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_actual_heal_attribute_projection_service import (
    ExtremeActualHealAttributeProjectionResult,
)
from services.extreme_actual_heal_champion_point_candidate_service import (
    ExtremeActualHealChampionPointCandidateResult,
)
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)


def _optimizer():
    return SimpleNamespace(database_path=Path("ignored.db"))


class _ChampionPointCandidates:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def build_candidates(self, build, *, character_id, baseline_build_id):
        self.calls.append((build, character_id, baseline_build_id))
        return self.result


class _AttributeProjection:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def build_candidates(
        self,
        build,
        *,
        entity_id,
        character_id,
        baseline_build_id,
    ):
        self.calls.append(
            (build, entity_id, character_id, baseline_build_id)
        )
        return self.result


def test_standing_optimizer_defaults_to_canonical_healing_event_service():
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
    )

    assert isinstance(service.healing_events, ExtremeCanonicalHealingEventService)


def test_explicit_healing_event_evaluator_remains_authoritative():
    custom = object()
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
        healing_events=custom,
    )

    assert service.healing_events is custom


def test_standing_optimizer_uses_injected_champion_point_candidate_search():
    cp = _ChampionPointCandidates(
        ExtremeActualHealChampionPointCandidateResult(
            unresolved=("heal-relevant CP gap",),
        )
    )
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
        healing_events=object(),
        champion_point_candidates=cp,
    )

    candidates = service._additional_candidates(
        PlayerBuild(),
        progression=object(),
        character_id="character",
        baseline_build_id="build",
        entity_id="heal",
        active_bar="front",
    )

    assert candidates == ()
    assert len(cp.calls) == 1
    assert cp.calls[0][1:] == ("character", "build")
    assert service._champion_point_search_unresolved == ("heal-relevant CP gap",)


def test_standing_optimizer_uses_proved_attribute_projection():
    sentinel = object()
    projection = _AttributeProjection(
        ExtremeActualHealAttributeProjectionResult(
            candidates=(sentinel,),
            source_allocations_reviewed=2145,
            denominator_proven=True,
            search_scope=("all 2,145 allocations proof-reduced",),
        )
    )
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
        healing_events=object(),
        attribute_projection=projection,
    )
    service._attribute_search_entity_id = "combat_prayer"

    candidates = service._resource_attribute_candidates(
        PlayerBuild(),
        character_id="character",
        baseline_build_id="build",
    )

    assert candidates == (sentinel,)
    assert projection.calls[0][1:] == ("combat_prayer", "character", "build")
    assert service._attribute_search_unresolved == ()
    assert service._attribute_search_scope == ("all 2,145 allocations proof-reduced",)


def test_failed_attribute_projection_falls_back_and_preserves_proof_gap():
    projection = _AttributeProjection(
        ExtremeActualHealAttributeProjectionResult(
            candidates=(),
            source_allocations_reviewed=2145,
            denominator_proven=False,
            unresolved=("unsupported coefficient family",),
        )
    )
    service = ExtremeCanonicalActualHealOptimizationService(
        optimizer=_optimizer(),
        healing_events=object(),
        attribute_projection=projection,
    )
    service._attribute_search_entity_id = "odd_heal"

    candidates = service._resource_attribute_candidates(
        PlayerBuild(AttributeHealth=10, AttributeMagicka=44, AttributeStamina=10),
        character_id="character",
        baseline_build_id="build",
    )

    allocations = {
        (
            candidate.candidate_build.AttributeHealth,
            candidate.candidate_build.AttributeMagicka,
            candidate.candidate_build.AttributeStamina,
        )
        for candidate in candidates
    }
    assert allocations == {(64, 0, 0), (0, 64, 0), (0, 0, 64)}
    assert service._attribute_search_unresolved == ("unsupported coefficient family",)
