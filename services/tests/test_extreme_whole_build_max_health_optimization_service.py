from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_whole_build_max_health_optimization_service import (
    ExtremeWholeBuildMaxHealthOptimizationService,
)


class _PackageSource:
    def __init__(self, token: str):
        self.token = token
        self.calls = []

    def build_candidates(self, baseline_build, **kwargs):
        self.calls.append(dict(kwargs))
        return (self.token,)


def _service() -> ExtremeWholeBuildMaxHealthOptimizationService:
    service = ExtremeWholeBuildMaxHealthOptimizationService.__new__(
        ExtremeWholeBuildMaxHealthOptimizationService
    )
    service._active_bar_for_package_search = "back"
    service.gear_set_candidates = _PackageSource("five")
    service.monster_packages = _PackageSource("monster")
    service.double_five_packages = _PackageSource("double-five")
    service.mythic_packages = _PackageSource("ring-mythic")
    service.non_ring_mythic_packages = _PackageSource("non-ring-mythic")
    service._race_candidates = lambda baseline_build, **kwargs: ("race",)
    return service


def test_max_health_candidate_search_extends_sheet_search_with_whole_build_families(monkeypatch):
    monkeypatch.setattr(
        ExtremeCompleteOptimizationService,
        "_candidates",
        lambda self, baseline_build, **kwargs: ("sheet",),
    )
    service = _service()

    candidates = service._candidates(
        PlayerBuild(BuildName="Health"),
        objective=SimpleNamespace(key="max_health"),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert candidates == (
        "sheet",
        "race",
        "five",
        "monster",
        "double-five",
        "ring-mythic",
        "non-ring-mythic",
    )


def test_mythic_package_discovery_uses_selected_active_bar(monkeypatch):
    monkeypatch.setattr(
        ExtremeCompleteOptimizationService,
        "_candidates",
        lambda self, baseline_build, **kwargs: (),
    )
    service = _service()

    service._candidates(
        PlayerBuild(BuildName="Health"),
        objective=SimpleNamespace(key="max_health"),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert service.mythic_packages.calls == [
        {
            "character_id": "char-1",
            "baseline_build_id": "build-1",
            "active_bar": "back",
        }
    ]
    assert service.non_ring_mythic_packages.calls == [
        {
            "character_id": "char-1",
            "baseline_build_id": "build-1",
            "active_bar": "back",
        }
    ]


def test_non_max_health_objectives_keep_parent_candidate_boundary(monkeypatch):
    monkeypatch.setattr(
        ExtremeCompleteOptimizationService,
        "_candidates",
        lambda self, baseline_build, **kwargs: ("sheet",),
    )
    service = _service()

    candidates = service._candidates(
        PlayerBuild(BuildName="Other"),
        objective=SimpleNamespace(key="spell_damage"),
        character_id="char-1",
        baseline_build_id="build-1",
    )

    assert candidates == ("sheet",)
    assert service.gear_set_candidates.calls == []
    assert service.monster_packages.calls == []
    assert service.double_five_packages.calls == []
    assert service.mythic_packages.calls == []
    assert service.non_ring_mythic_packages.calls == []


def test_whole_build_search_scope_names_resource_relevant_package_families():
    scope = ExtremeWholeBuildMaxHealthOptimizationService.SEARCH_SCOPE

    assert "race replacement" in scope
    assert "reviewed ordinary five-piece set replacement" in scope
    assert "reviewed legal five-piece + two-piece monster package" in scope
    assert "reviewed legal five-piece + five-piece package" in scope
    assert "reviewed legal five-piece + five-piece + ring mythic package" in scope
    assert "reviewed legal five-piece + five-piece + non-ring mythic package" in scope
