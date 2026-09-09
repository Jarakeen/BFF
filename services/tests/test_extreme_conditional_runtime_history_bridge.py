from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_runtime_snapshot import (
    ExtremeRuntimePotionUse,
    ExtremeRuntimeSnapshot,
)


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )


class _HealingEvents:
    pass


class _PotionCandidates:
    def __init__(self):
        self.calls = []

    def build_candidates(self, baseline_build, *, character_id, baseline_build_id):
        self.calls.append((baseline_build.BuildName, character_id, baseline_build_id))
        return ()


class _SkillCandidates:
    def __init__(self):
        self.triggered_calls = []

    def triggered_build_candidates(
        self,
        baseline_build,
        *,
        character_id,
        baseline_build_id,
        protected_entity_id,
        active_bar,
        event,
        snapshot_time_seconds,
        chance_roll,
        condition_context,
    ):
        self.triggered_calls.append(
            (
                baseline_build.BuildName,
                character_id,
                baseline_build_id,
                protected_entity_id,
                active_bar,
                event,
                snapshot_time_seconds,
                chance_roll,
                condition_context,
            )
        )
        return ()


def _attempt(*, time_seconds: float, sequence: int = 0) -> RuntimeEffectEventAttempt:
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=time_seconds,
            trigger="critical_heal",
            source="conditional healer runtime bridge test",
            sequence=sequence,
        ),
        chance_roll=0.25,
        condition_context=frozenset({"target_below_50"}),
    )


def test_conditional_healer_uses_unified_history_for_candidate_discovery():
    attempt = _attempt(time_seconds=4.0, sequence=2)
    potion_use = ExtremeRuntimePotionUse(time_seconds=8.0, sequence=1)
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(potion_use, attempt),
        snapshot_time_seconds=10.0,
    )
    potion_candidates = _PotionCandidates()
    skill_candidates = _SkillCandidates()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        runtime_snapshot=snapshot,
        potion_candidates=potion_candidates,
        skill_buff_candidates=skill_candidates,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    proposed = service._additional_candidates(
        PlayerBuild(BuildName="Unified Healer Runtime"),
        progression=CharacterProgression(),
        character_id="char-1",
        baseline_build_id="build-1",
        entity_id="blessing_of_protection",
        active_bar="front",
    )

    assert proposed == ()
    assert service.potion_elapsed_seconds == pytest.approx(2.0)
    assert potion_candidates.calls == [("Unified Healer Runtime", "char-1", "build-1")]
    assert len(skill_candidates.triggered_calls) == 1
    triggered = skill_candidates.triggered_calls[0]
    assert triggered[5] is attempt.event
    assert triggered[6] == pytest.approx(10.0)
    assert triggered[7] == pytest.approx(0.25)
    assert triggered[8] == frozenset({"target_below_50"})


def test_conditional_healer_ignores_future_unified_potion_use():
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(ExtremeRuntimePotionUse(time_seconds=12.0),),
        snapshot_time_seconds=10.0,
    )
    potion_candidates = _PotionCandidates()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        runtime_snapshot=snapshot,
        potion_candidates=potion_candidates,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    proposed = service._additional_candidates(
        PlayerBuild(BuildName="Future Potion Healer"),
        progression=CharacterProgression(),
        character_id="char-1",
        baseline_build_id="build-1",
        entity_id="blessing_of_protection",
        active_bar="front",
    )

    assert proposed == ()
    assert service.potion_elapsed_seconds is None
    assert potion_candidates.calls == []
