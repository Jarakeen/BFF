from __future__ import annotations

from types import SimpleNamespace

from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_static_optimization_record_adapter import (
    ExtremeStaticOptimizationRecordAdapter,
)


class _Build:
    def __init__(self, payload):
        self.payload = dict(payload)

    def to_dict(self):
        return dict(self.payload)


def _result(*, key="max_health", ratio=False, unresolved=(), omitted=("race change",)):
    return SimpleNamespace(
        objective=SimpleNamespace(key=key, ratio=ratio),
        optimized_value=54321.0,
        optimized_build=_Build({"BuildName": "Extreme Test"}),
        unresolved=tuple(unresolved),
        search_scope=("attribute allocation", "Mundus"),
        omitted_scope=tuple(omitted),
    )


def test_static_adapter_preserves_value_and_winning_build_snapshot():
    record = ExtremeStaticOptimizationRecordAdapter().adapt(_result())

    assert record.objective_key == "max_health"
    assert record.raw_value == 54321.0
    assert record.winning_build == {"BuildName": "Extreme Test"}
    assert record.unit == "points"


def test_static_adapter_is_truthfully_lower_bound_not_global_proof():
    record = ExtremeStaticOptimizationRecordAdapter().adapt(_result())

    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert not record.globally_proven
    assert not record.search_coverage.denominator_proven
    assert record.search_coverage.searched == ("attribute allocation", "Mundus")
    assert record.search_coverage.omitted == ("race change",)


def test_static_adapter_preserves_unresolved_diagnostics_without_duplication():
    record = ExtremeStaticOptimizationRecordAdapter().adapt(
        _result(unresolved=("unresolved trait", "unresolved trait", "other"))
    )

    assert record.unresolved == ("unresolved trait", "other")


def test_static_adapter_marks_ratio_objectives_as_ratio_units():
    record = ExtremeStaticOptimizationRecordAdapter().adapt(
        _result(key="healing_done", ratio=True)
    )

    assert record.unit == "ratio"


def test_static_adapter_marks_recovery_objectives_as_rating_units():
    record = ExtremeStaticOptimizationRecordAdapter().adapt(
        _result(key="magicka_recovery")
    )

    assert record.unit == "rating"
