from __future__ import annotations

from types import SimpleNamespace

from minmax.build_candidate import BuildCandidate, BuildChange
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)


def _candidate(name: str, candidate_id: str) -> BuildCandidate:
    build = PlayerBuild.from_dict({"Name": "Magrat", "BuildName": name})
    return BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(
            BuildChange.from_values(
                path="BuildName",
                before="DF Healer",
                after=name,
                source="test:incumbent-admission",
            ),
        ),
        candidate_source="test:incumbent-admission",
    )


class _FakeCompleteOptimizer:
    database_path = None

    def __init__(self) -> None:
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )

    @staticmethod
    def objective(_key):
        return object()

    @staticmethod
    def _candidates(current, *, objective, character_id, baseline_build_id):
        _ = (objective, character_id, baseline_build_id)
        if current.BuildName != "DF Healer":
            return ()
        return (
            _candidate("Risky", "candidate-risky"),
            _candidate("Safe", "candidate-safe"),
        )


class _FakeProgressionAdapter:
    def __init__(self, _catalog_service) -> None:
        pass

    @staticmethod
    def resolve(_build):
        return SimpleNamespace(
            resolved=True,
            progression=SimpleNamespace(),
            character_id="magrat",
            unresolved=(),
        )


class _Harness(ExtremeActualHealOptimizationService):
    @staticmethod
    def _resource_attribute_candidates(*args, **kwargs):
        return ()

    def _race_candidates(self, *args, **kwargs):
        return ()

    def _additional_candidates(self, *args, **kwargs):
        return ()

    def _evaluate_cached(
        self,
        build,
        *,
        progression,
        character_id,
        build_id,
        entity_id,
        active_bar,
        evaluation_cache,
    ):
        _ = (
            progression,
            character_id,
            build_id,
            active_bar,
            evaluation_cache,
        )
        values = {
            "DF Healer": (100.0, ()),
            # Numerically strongest, but it introduces a new proof blocker and
            # therefore must never replace the clean incumbent.
            "Risky": (300.0, ("new unresolved mechanic",)),
            "Safe": (200.0, ()),
        }
        score, unresolved = values[build.BuildName]
        return (
            SimpleNamespace(
                entity_id=entity_id,
                critical_heal=score,
                mechanic_complete=not unresolved,
            ),
            unresolved,
        )


def test_higher_scoring_new_blocker_cannot_crowd_out_clean_candidate(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "MinmaxCharacterProgressionAdapter",
        _FakeProgressionAdapter,
    )
    service = _Harness(
        optimizer=_FakeCompleteOptimizer(),
        healing_events=SimpleNamespace(),
    )
    baseline = PlayerBuild.from_dict({"Name": "Magrat", "BuildName": "DF Healer"})

    result = service.optimize(baseline, "fixture-heal", max_passes=2)

    assert result.optimized_build.BuildName == "Safe"
    assert result.optimized_event.critical_heal == 200.0
    assert result.unresolved == ()
    assert len(result.steps) == 1
    assert result.steps[0].critical_heal_before == 100.0
    assert result.steps[0].critical_heal_after == 200.0
