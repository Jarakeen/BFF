from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from models.combat_simulation import CombatSimulationResult
from services.extreme_saved_rotation_combat_record_service import (
    ExtremeSavedRotationCombatRecordService,
)


class _ArtifactService:
    def __init__(self, plan):
        self.plan = plan

    def get_rotation_plan(self, build_id):
        assert build_id == "build-dd"
        return self.plan


class _CatalogService:
    def resolve_build_id(self, build):
        del build
        return "build-dd"


class _Simulator:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def simulate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _SummaryService:
    def __init__(self, summary):
        self.summary = summary
        self.calls = []

    def summarize(self, result, *, target_identity):
        self.calls.append((result, target_identity))
        return self.summary


def _build(role="DD"):
    return PlayerBuild(
        Name="Damage Tester",
        BuildName="Parse",
        Role=role,
    )


def _plan():
    return RotationPlan(
        character_name="Damage Tester",
        build_name="Parse",
        duration_seconds=10.0,
        actions=(),
    )


def _service(summary, *, plan=None):
    result = CombatSimulationResult(
        duration_seconds=10.0,
        initial_bar="front",
        final_bar="front",
        events=(),
    )
    simulator = _Simulator(result)
    summary_service = _SummaryService(summary)
    service = ExtremeSavedRotationCombatRecordService(
        "data/eso.db",
        artifact_service=_ArtifactService(plan if plan is not None else _plan()),
        catalog_service=_CatalogService(),
        simulator=simulator,
        summary_service=summary_service,
    )
    return service, simulator, summary_service


def test_sustained_dps_consumes_saved_rotation_and_explicit_target_assumptions() -> None:
    summary = SimpleNamespace(
        duration_seconds=10.0,
        modeled_dps=120000.0,
        attempted_damage=1_200_000.0,
        applied_damage=1_200_000.0,
        total_overkill=0.0,
        ending_target_health=20_000_000,
        target_dead=False,
        killing_source=None,
        complete_damage_evidence=True,
        damage_unresolved=(),
    )
    service, simulator, summary_service = _service(summary)

    result = service.sustained_dps(
        _build(),
        target_health=21_200_000,
        target_resistance=18200.0,
        target_name="Trial Dummy",
    )

    assert result.record is not None
    assert result.record.modeled_dps == pytest.approx(120000.0)
    assert result.record.applied_damage == pytest.approx(1_200_000.0)
    assert result.record.duration_seconds == pytest.approx(10.0)
    assert result.record.target_dead is False
    assert result.record.damage_complete is True
    assert any("Global Extreme sustained-DPS search" in row for row in result.unresolved)

    assert len(simulator.calls) == 1
    call = simulator.calls[0]
    assert call["damage_target_identity"] == "Trial Dummy"
    assert call["target_resistance"] == pytest.approx(18200.0)
    target = call["target_state"].combatant("Trial Dummy")
    assert target is not None
    assert target.current_health == 21_200_000
    assert target.maximum_health == 21_200_000
    assert summary_service.calls == [(simulator.result, "Trial Dummy")]


def test_sustained_dps_withholds_record_when_damage_evidence_is_incomplete() -> None:
    summary = SimpleNamespace(
        duration_seconds=10.0,
        modeled_dps=None,
        attempted_damage=100000.0,
        applied_damage=50000.0,
        total_overkill=0.0,
        ending_target_health=950000,
        target_dead=False,
        killing_source=None,
        complete_damage_evidence=False,
        damage_unresolved=("periodic damage timing unresolved",),
    )
    service, _simulator, _summary_service = _service(summary)

    result = service.sustained_dps(
        _build(),
        target_health=1_000_000,
        target_resistance=18200.0,
    )

    assert result.record is None
    assert "periodic damage timing unresolved" in result.unresolved


def test_sustained_dps_rejects_non_dd_build_without_running_simulation() -> None:
    summary = SimpleNamespace()
    service, simulator, _summary_service = _service(summary)

    result = service.sustained_dps(
        _build(role="Healer"),
        target_health=1_000_000,
        target_resistance=18200.0,
    )

    assert result.record is None
    assert result.unresolved == ("MOST Sustained DPS requires a saved DD/DPS build",)
    assert simulator.calls == []


def test_sustained_dps_requires_positive_health_and_nonnegative_resistance() -> None:
    summary = SimpleNamespace()
    service, _simulator, _summary_service = _service(summary)

    with pytest.raises(ValueError, match="target_health must be positive"):
        service.sustained_dps(
            _build(),
            target_health=0,
            target_resistance=18200.0,
        )

    with pytest.raises(ValueError, match="target_resistance cannot be negative"):
        service.sustained_dps(
            _build(),
            target_health=1_000_000,
            target_resistance=-1.0,
        )
