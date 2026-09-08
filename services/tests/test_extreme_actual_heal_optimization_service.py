from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)


class _Event:
    def __init__(self, entity_id: str, critical_heal: float | None, unresolved=()):
        self.entity_id = entity_id
        self.critical_heal = critical_heal
        self.normal_heal = None if critical_heal is None else critical_heal / 1.5
        self.unresolved = tuple(unresolved)
        self.mechanic_complete = critical_heal is not None and not self.unresolved


class _HealingEvents:
    def evaluate(self, *, build, context, entity_id):
        _ = context
        critical = 100.0 + float(build.AttributeMagicka or 0)
        unresolved = ("rejected health candidate blocker",) if int(build.AttributeHealth or 0) == 64 else ()
        return _Event(entity_id, critical, unresolved)


class _ContextFactory:
    def __init__(self):
        self.progressions = []

    def build(self, **kwargs):
        self.progressions.append(kwargs["progression"])
        return SimpleNamespace(unresolved_gear_effects=())


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = _ContextFactory()

    @staticmethod
    def objective(key):
        return SimpleNamespace(key=key)

    @staticmethod
    def _candidates(*args, **kwargs):
        _ = args, kwargs
        return ()


def _install_progression_adapter(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(
            attributes=AttributeAllocation(),
            passive_ranks={},
            passive_cp_points={},
        ),
        unresolved=(),
    )

    class _Adapter:
        def __init__(self, catalog):
            _ = catalog

        def resolve(self, build):
            _ = build
            return resolution

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)


def test_actual_heal_resource_candidates_cover_all_three_attribute_extremes():
    baseline = PlayerBuild(
        BuildName="Heal Baseline",
        AttributeHealth=10,
        AttributeMagicka=44,
        AttributeStamina=10,
    )

    candidates = ExtremeActualHealOptimizationService._resource_attribute_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
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
    assert (baseline.AttributeHealth, baseline.AttributeMagicka, baseline.AttributeStamina) == (10, 44, 10)


def test_actual_heal_optimizer_selects_largest_critical_event(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )
    baseline = PlayerBuild(BuildName="Heal Baseline")

    result = service.optimize(
        baseline,
        "blessing_of_protection",
        max_passes=3,
    )

    assert result.baseline_event.critical_heal == pytest.approx(100.0)
    assert result.optimized_event.critical_heal == pytest.approx(164.0)
    assert result.optimized_build.AttributeMagicka == 64
    assert result.gain == pytest.approx(64.0)
    assert len(result.steps) == 1
    assert result.steps[0].path == "Attributes"


def test_rejected_candidate_blocker_does_not_contaminate_selected_build(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Heal Baseline"),
        "blessing_of_protection",
        max_passes=2,
    )

    assert result.optimized_build.AttributeMagicka == 64
    assert result.unresolved == ()
    assert result.mechanic_complete is True


def test_progression_override_survives_every_candidate_context_rebuild(monkeypatch):
    _install_progression_adapter(monkeypatch)
    optimizer = _Optimizer()
    service = ExtremeActualHealOptimizationService(
        optimizer=optimizer,
        healing_events=_HealingEvents(),
    )
    override = CharacterProgression(
        owned_skill_lines=("animal_companions", "restoring_light"),
        passive_ranks={"Flourish": 2, "Mending": 2},
        passive_cp_points={"Blessed": 20},
    )

    service.optimize(
        PlayerBuild(BuildName="Hypothetical Healer"),
        "blessing_of_protection",
        max_passes=2,
        progression_override=override,
    )

    assert optimizer.context_factory.progressions
    assert all(
        progression.owned_skill_lines == override.owned_skill_lines
        for progression in optimizer.context_factory.progressions
    )
    assert all(
        progression.passive_rank("Flourish") == 2
        and progression.passive_rank("Mending") == 2
        and progression.passive_cp_allocation("Blessed") == 20
        for progression in optimizer.context_factory.progressions
    )
    assert {
        (
            progression.attributes.health,
            progression.attributes.magicka,
            progression.attributes.stamina,
        )
        for progression in optimizer.context_factory.progressions
    } >= {(0, 0, 0), (64, 0, 0), (0, 64, 0), (0, 0, 64)}


def test_actual_heal_score_refuses_missing_critical_event():
    with pytest.raises(ValueError, match="critical healing event is unresolved"):
        ExtremeActualHealOptimizationService._score(
            _Event("unresolved_heal", None, ("missing coefficient",))
        )
