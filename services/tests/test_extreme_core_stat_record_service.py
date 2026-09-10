from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.extreme_core_stat_record_service import ExtremeCoreStatRecordService
from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


@dataclass
class _Objective:
    key: str


@dataclass
class _OptimizationResult:
    objective: _Objective


class _Optimizer:
    def __init__(self) -> None:
        self.calls = []

    def optimize(self, build, objective_key, *, active_bar="front", max_passes=24):
        self.calls.append((build, objective_key, active_bar, max_passes))
        return _OptimizationResult(objective=_Objective(objective_key))


class _Adapter:
    def __init__(self, *, mismatch: str | None = None) -> None:
        self.mismatch = mismatch
        self.seen = []

    def adapt(self, result):
        self.seen.append(result)
        key = self.mismatch or result.objective.key
        return ExtremeRecordResult.for_objective(
            key,
            raw_value=123.0,
            proof_status=ExtremeRecordProofStatus.LOWER_BOUND,
            search_coverage=ExtremeRecordSearchCoverage(
                searched=("fixture",),
                omitted=("global denominator",),
                denominator_proven=False,
            ),
        )


def test_supported_objectives_match_current_static_optimizer_order():
    keys = tuple(objective.key for objective in ExtremeCoreStatRecordService.supported_objectives())
    assert keys == (
        "max_health",
        "max_magicka",
        "max_stamina",
        "health_recovery",
        "magicka_recovery",
        "stamina_recovery",
        "weapon_damage",
        "spell_damage",
        "physical_resistance",
        "spell_resistance",
        "physical_penetration",
        "spell_penetration",
        "weapon_critical",
        "spell_critical",
        "critical_damage",
        "healing_done",
    )


def test_supports_normalizes_keys_and_rejects_non_static_record_objectives():
    assert ExtremeCoreStatRecordService.supports(" Weapon_Damage ") is True
    assert ExtremeCoreStatRecordService.supports("critical_heal") is False
    assert ExtremeCoreStatRecordService.supports("") is False


def test_record_for_build_runs_optimizer_and_returns_canonical_record():
    optimizer = _Optimizer()
    adapter = _Adapter()
    service = ExtremeCoreStatRecordService(optimizer=optimizer, adapter=adapter)
    build = object()

    record = service.record_for_build(
        build,
        " Weapon_Damage ",
        active_bar="back",
        max_passes=7,
    )

    assert record.objective_key == "weapon_damage"
    assert record.raw_value == 123.0
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert optimizer.calls == [(build, "weapon_damage", "back", 7)]
    assert len(adapter.seen) == 1


def test_cataloged_but_not_executable_objective_fails_closed_before_optimizer_call():
    optimizer = _Optimizer()
    service = ExtremeCoreStatRecordService(optimizer=optimizer, adapter=_Adapter())

    with pytest.raises(ValueError, match="cataloged but is not yet executable"):
        service.record_for_build(object(), "critical_heal")

    assert optimizer.calls == []


def test_unknown_objective_uses_canonical_catalog_error():
    service = ExtremeCoreStatRecordService(optimizer=_Optimizer(), adapter=_Adapter())

    with pytest.raises(ValueError, match="Unsupported Extreme Records objective"):
        service.record_for_build(object(), "banana_velocity")


def test_records_for_build_preserves_requested_order_and_parameters():
    optimizer = _Optimizer()
    service = ExtremeCoreStatRecordService(optimizer=optimizer, adapter=_Adapter())
    build = object()

    records = service.records_for_build(
        build,
        objective_keys=("spell_damage", "max_health", "magicka_recovery"),
        active_bar="back",
        max_passes=3,
    )

    assert tuple(record.objective_key for record in records) == (
        "spell_damage",
        "max_health",
        "magicka_recovery",
    )
    assert [call[1:] for call in optimizer.calls] == [
        ("spell_damage", "back", 3),
        ("max_health", "back", 3),
        ("magicka_recovery", "back", 3),
    ]


def test_adapter_objective_mismatch_fails_closed():
    service = ExtremeCoreStatRecordService(
        optimizer=_Optimizer(),
        adapter=_Adapter(mismatch="spell_damage"),
    )

    with pytest.raises(ValueError, match="mismatched objective"):
        service.record_for_build(object(), "weapon_damage")
