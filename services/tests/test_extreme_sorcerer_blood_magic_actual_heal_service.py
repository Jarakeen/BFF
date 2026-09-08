from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_sorcerer_blood_magic_actual_heal_service import (
    ExtremeSorcererBloodMagicActualHealService,
)
from services.extreme_whole_build_max_health_optimization_service import (
    ExtremeWholeBuildMaxHealthOptimizationService,
)


class _FakeOptimizer:
    def __init__(self, *, baseline_value=20_000.0, optimized_value=50_000.0, unresolved=()):
        self.baseline_value = float(baseline_value)
        self.optimized_value = float(optimized_value)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def optimize(self, baseline_build, objective_key, *, active_bar="front", max_passes=24):
        self.calls.append((objective_key, active_bar, max_passes))
        optimized = PlayerBuild.from_dict(baseline_build.to_dict())
        return SimpleNamespace(
            baseline_build=PlayerBuild.from_dict(baseline_build.to_dict()),
            optimized_build=optimized,
            baseline_value=self.baseline_value,
            optimized_value=self.optimized_value,
            unresolved=self.unresolved,
            search_scope=("canonical max-health test search",),
            omitted_scope=("test optimizer omitted surface",),
        )


def _build() -> PlayerBuild:
    return PlayerBuild(Name="Test Sorcerer", BuildName="Blood Magic")


def test_blood_magic_lane_defaults_to_whole_build_max_health_optimizer():
    service = ExtremeSorcererBloodMagicActualHealService()

    assert isinstance(service.optimizer, ExtremeWholeBuildMaxHealthOptimizationService)


def test_blood_magic_lane_optimizes_canonical_max_health():
    optimizer = _FakeOptimizer(baseline_value=20_000.0, optimized_value=50_000.0)
    service = ExtremeSorcererBloodMagicActualHealService(optimizer=optimizer)

    result = service.optimize(_build(), active_bar="back", max_passes=7)

    assert service.optimizer is optimizer
    assert optimizer.calls == [("max_health", "back", 7)]
    assert result.baseline_max_health == 20_000.0
    assert result.optimized_max_health == 50_000.0
    assert result.baseline_event.normal_heal == 2_000.0
    assert result.optimized_event.normal_heal == 5_000.0
    assert result.normal_heal_gain == 3_000.0


def test_blood_magic_lane_uses_noncritical_max_health_proc_policy():
    service = ExtremeSorcererBloodMagicActualHealService(
        optimizer=_FakeOptimizer(baseline_value=30_000.0, optimized_value=40_000.0)
    )

    result = service.optimize(_build())

    assert result.optimized_event.normal_heal == 4_000.0
    assert result.optimized_event.can_crit is False
    assert result.mechanic_complete is True
    assert "Blood Magic critical-heal eligibility" not in result.omitted_scope
    assert "Blood Magic Max-Health passive-proc critical policy: non-critical" in result.search_scope


def test_blood_magic_lane_preserves_optimizer_unresolved_evidence():
    service = ExtremeSorcererBloodMagicActualHealService(
        optimizer=_FakeOptimizer(unresolved=("unresolved gear effect",))
    )

    result = service.optimize(_build())

    assert result.unresolved == ("unresolved gear effect",)
    assert result.mechanic_complete is False


def test_blood_magic_lane_reports_optimizer_search_boundary_without_stale_package_or_crit_omissions():
    service = ExtremeSorcererBloodMagicActualHealService(optimizer=_FakeOptimizer())

    result = service.optimize(_build())

    assert "Blood Magic U50 rank-2 heal amount: 10% of canonical Max Health" in result.search_scope
    assert "canonical max-health test search" in result.search_scope
    assert "test optimizer omitted surface" in result.omitted_scope
    assert "Blood Magic critical-heal eligibility" not in result.omitted_scope
    assert not any("race replacement beyond" in item for item in result.omitted_scope)
    assert not any("gear-set/package replacement beyond" in item for item in result.omitted_scope)
