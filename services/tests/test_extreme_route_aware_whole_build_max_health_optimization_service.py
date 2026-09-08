from models.build_model import PlayerBuild
from services.extreme_route_aware_whole_build_max_health_optimization_service import (
    ExtremeRouteAwareWholeBuildMaxHealthOptimizationService,
)
from services.extreme_whole_build_max_health_optimization_service import (
    ExtremeWholeBuildMaxHealthOptimizationService,
)


def test_route_progression_override_reaches_candidate_evaluation_and_clears(monkeypatch):
    saved_progression = object()
    route_progression = object()
    observed = []

    def fake_parent_optimize(self, baseline_build, objective_key, *, active_bar="front", max_passes=24):
        return self._evaluate(
            baseline_build,
            progression=saved_progression,
            character_id="char",
            build_id="build",
            objective=object(),
            active_bar=active_bar,
        )

    def fake_parent_evaluate(
        self,
        build,
        *,
        progression,
        character_id,
        build_id,
        objective,
        active_bar,
    ):
        observed.append(progression)
        return progression

    monkeypatch.setattr(
        ExtremeWholeBuildMaxHealthOptimizationService,
        "optimize",
        fake_parent_optimize,
    )
    monkeypatch.setattr(
        ExtremeWholeBuildMaxHealthOptimizationService,
        "_evaluate",
        fake_parent_evaluate,
    )

    service = ExtremeRouteAwareWholeBuildMaxHealthOptimizationService.__new__(
        ExtremeRouteAwareWholeBuildMaxHealthOptimizationService
    )
    service._route_progression_override = None

    result = service.optimize(
        PlayerBuild(BuildName="Route"),
        "max_health",
        active_bar="back",
        progression_override=route_progression,
    )

    assert result is route_progression
    assert observed == [route_progression]
    assert service._route_progression_override is None


def test_without_override_saved_progression_remains_authoritative(monkeypatch):
    saved_progression = object()

    def fake_parent_optimize(self, baseline_build, objective_key, *, active_bar="front", max_passes=24):
        return self._evaluate(
            baseline_build,
            progression=saved_progression,
            character_id="char",
            build_id="build",
            objective=object(),
            active_bar=active_bar,
        )

    def fake_parent_evaluate(self, build, *, progression, **kwargs):
        return progression

    monkeypatch.setattr(
        ExtremeWholeBuildMaxHealthOptimizationService,
        "optimize",
        fake_parent_optimize,
    )
    monkeypatch.setattr(
        ExtremeWholeBuildMaxHealthOptimizationService,
        "_evaluate",
        fake_parent_evaluate,
    )

    service = ExtremeRouteAwareWholeBuildMaxHealthOptimizationService.__new__(
        ExtremeRouteAwareWholeBuildMaxHealthOptimizationService
    )
    service._route_progression_override = None

    result = service.optimize(PlayerBuild(BuildName="Saved"), "max_health")

    assert result is saved_progression
    assert service._route_progression_override is None
