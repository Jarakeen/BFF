from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_optimization_service as module
from services.extreme_optimization_service import (
    ExtremeOptimizationService,
    format_extreme_value,
)


def test_max_health_attribute_candidate_moves_all_points_to_health_without_mutating_baseline():
    baseline = PlayerBuild(
        BuildName="Baseline",
        AttributeHealth=20,
        AttributeMagicka=44,
        AttributeStamina=0,
    )
    objective = ExtremeOptimizationService.objective("max_health")

    candidates = ExtremeOptimizationService._attribute_candidates(
        baseline,
        objective=objective,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert len(candidates) == 1
    candidate = candidates[0].candidate_build
    assert (candidate.AttributeHealth, candidate.AttributeMagicka, candidate.AttributeStamina) == (64, 0, 0)
    assert (baseline.AttributeHealth, baseline.AttributeMagicka, baseline.AttributeStamina) == (20, 44, 0)
    assert candidates[0].changes[0].path == "Attributes"


def test_extreme_value_formatter_keeps_ratios_human_readable():
    assert format_extreme_value(ExtremeOptimizationService.objective("max_health"), 54321) == "54,321"
    assert format_extreme_value(ExtremeOptimizationService.objective("spell_critical"), 0.4375) == "43.75%"


def test_optimizer_can_accept_proven_stat_gain_even_when_unrelated_effects_are_unresolved(monkeypatch):
    baseline = PlayerBuild(
        BuildName="Baseline",
        AttributeHealth=0,
        AttributeMagicka=64,
        AttributeStamina=0,
    )

    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(attributes=AttributeAllocation(magicka=64)),
        unresolved=(),
    )

    class FakeAdapter:
        def __init__(self, _catalog):
            pass

        def resolve(self, _build):
            return resolution

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", FakeAdapter)

    service = ExtremeOptimizationService.__new__(ExtremeOptimizationService)
    service.build_service = SimpleNamespace(canonical=SimpleNamespace(catalog_service=object()))

    def fake_evaluate(build, **_kwargs):
        return float(build.AttributeHealth), ("unrelated dynamic set effect unresolved",)

    service._evaluate = fake_evaluate
    service._candidates = lambda build, **kwargs: ExtremeOptimizationService._attribute_candidates(
        build,
        objective=kwargs["objective"],
        character_id=kwargs["character_id"],
        baseline_build_id=kwargs["baseline_build_id"],
    )

    result = service.optimize(baseline, "max_health", max_passes=3)

    assert result.optimized_value == 64.0
    assert result.optimized_build.AttributeHealth == 64
    assert len(result.steps) == 1
    assert "unrelated dynamic set effect unresolved" in result.unresolved


def test_tools_navigation_exposes_extreme_build_lab():
    from ui.components.foundry_sidebar import CORE_NAV_SECTIONS

    tool_section = next(
        section
        for section in CORE_NAV_SECTIONS
        if isinstance(section, dict) and section.get("label") == "Tool"
    )

    assert ("Extreme Build Lab", "extreme_optimization") in tool_section["children"]
