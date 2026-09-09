from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_maximum_healing_event_finalist_optimization_service import (
    ExtremeMaximumHealingEventFinalistOptimizationService,
)
from services.extreme_maximum_healing_event_finalist_selection_service import (
    ExtremeMaximumHealingEventFinalistSelectionResult,
)


class _Normalizer:
    def __init__(self, tag):
        self.tag = tag
        self.calls = []

    def normalize(self, progression, route):
        self.calls.append((progression, route))
        return f"{self.tag}:{','.join(route.equipped_skill_lines)}"


class _Optimizer:
    def __init__(self):
        self.calls = []

    def optimize(self, build, entity_id, **kwargs):
        self.calls.append((build, entity_id, kwargs))
        return SimpleNamespace(optimized_event=SimpleNamespace(critical_heal=200.0), unresolved=())


class _BloodOptimizer:
    def __init__(self):
        self.calls = []

    def optimize(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return SimpleNamespace(optimized_event=SimpleNamespace(normal_heal=150.0), unresolved=())


class _Ordinary:
    def __init__(self):
        self.optimizer = _Optimizer()
        self.progression_normalizer = _Normalizer("ordinary")
        self.progression_calls = 0

    def _progression(self, build):
        self.progression_calls += 1
        return "ordinary-base"


class _Blood:
    def __init__(self):
        self.blood_magic = _BloodOptimizer()
        self.progression_normalizer = _Normalizer("blood")
        self.progression_calls = 0

    def _progression(self, build):
        self.progression_calls += 1
        return "blood-base"


class _Selector:
    def __init__(self, finalists):
        self.finalists = tuple(finalists)

    def select(self, screening, **kwargs):
        _ = screening, kwargs
        return ExtremeMaximumHealingEventFinalistSelectionResult(
            finalists=self.finalists,
            screened_scored_entries=len(self.finalists),
            exact_duplicates_removed=0,
            represented_families=len(self.finalists),
            max_families=8,
            routes_per_family=3,
            omitted_scope=("shortlist pruning",),
        )


class _Aggregator:
    @staticmethod
    def _ordinary_entry(entry):
        return SimpleNamespace(
            source_kind="ordinary_skill",
            source_name=entry.candidate.name,
            event_value=float(entry.optimization.optimized_event.critical_heal),
            mechanic_complete=True,
        )

    @staticmethod
    def _blood_magic_entry(entry):
        return SimpleNamespace(
            source_kind="blood_magic",
            source_name=f"Blood Magic via {entry.trigger.name}",
            event_value=float(entry.optimization.optimized_event.normal_heal),
            mechanic_complete=True,
        )

    @staticmethod
    def _rank_key(entry):
        return (-float(entry.event_value), entry.source_name)


def _route(*lines):
    return SimpleNamespace(equipped_skill_lines=tuple(lines))


def test_stage_two_optimizes_only_selected_concrete_entries_with_route_progression():
    ordinary_source = SimpleNamespace(
        route=_route("animal_companions", "daedric_summoning", "green_balance"),
        candidate=SimpleNamespace(name="Summon Twilight Matriarch", entity_id="summon_twilight_matriarch"),
        slotted_index=0,
        candidate_build=PlayerBuild(BuildName="Matriarch finalist"),
    )
    blood_source = SimpleNamespace(
        route=_route("dark_magic", "green_balance", "winters_embrace"),
        trigger=SimpleNamespace(name="Dark Exchange"),
        slotted_index=1,
        candidate_build=PlayerBuild(BuildName="Blood finalist"),
    )
    finalists = (
        SimpleNamespace(source_kind="ordinary_skill", route_entry=ordinary_source),
        SimpleNamespace(source_kind="blood_magic", route_entry=blood_source),
    )
    ordinary = _Ordinary()
    blood = _Blood()
    service = ExtremeMaximumHealingEventFinalistOptimizationService(
        ordinary=ordinary,
        blood_magic=blood,
        selector=_Selector(finalists),
        aggregator=_Aggregator(),
    )
    screening = SimpleNamespace(omitted_scope=("screen omission",))

    result = service.optimize(
        PlayerBuild(BuildName="Baseline"),
        screening,
        active_bar="back",
        max_passes=4,
    )

    assert ordinary.progression_calls == 1
    assert blood.progression_calls == 1
    assert len(ordinary.optimizer.calls) == 1
    assert len(blood.blood_magic.calls) == 1
    ordinary_call = ordinary.optimizer.calls[0]
    assert ordinary_call[1] == "summon_twilight_matriarch"
    assert ordinary_call[2]["active_bar"] == "back"
    assert ordinary_call[2]["max_passes"] == 4
    assert ordinary_call[2]["progression_override"].startswith("ordinary:")
    blood_call = blood.blood_magic.calls[0]
    assert blood_call[1]["active_bar"] == "back"
    assert blood_call[1]["max_passes"] == 4
    assert blood_call[1]["progression_override"].startswith("blood:")
    assert [entry.event_value for entry in result.entries] == [200.0, 150.0]
    assert result.best_scored.event_value == 200.0
    assert result.global_maximum_proven is False
    assert "shortlist pruning" in result.omitted_scope
    assert "screen omission" in result.omitted_scope
