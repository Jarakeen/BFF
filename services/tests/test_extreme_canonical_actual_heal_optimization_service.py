from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.build_model import PlayerBuild
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
