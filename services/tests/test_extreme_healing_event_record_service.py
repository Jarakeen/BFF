from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_healing_event_record_service import ExtremeHealingEventRecordService


class _Catalog:
    def __init__(self) -> None:
        self.calls = []
        winner = SimpleNamespace(critical_heal=123456.0, mechanic_complete=True)
        self.result = SimpleNamespace(
            best_scored=winner,
            best_complete=winner,
            global_maximum_proven=False,
        )

    def rank(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


def test_heal_event_pair_runs_expensive_catalog_search_once() -> None:
    catalog = _Catalog()
    service = ExtremeHealingEventRecordService(catalog=catalog)
    build = SimpleNamespace(Name="Extreme Witness")

    actual, critical = service.evaluate_pair(build, active_bar="back", max_passes=7)

    assert len(catalog.calls) == 1
    assert catalog.calls[0][1] == {
        "active_bar": "back",
        "max_passes": 7,
        "include_base_class_changes": True,
    }
    assert actual.objective_key == "actual_heal"
    assert critical.objective_key == "critical_heal"
    assert actual.catalog is critical.catalog is catalog.result
    assert actual.best_scored_value == pytest.approx(123456.0)
    assert critical.best_scored_value == pytest.approx(123456.0)


def test_heal_event_projection_preserves_underlying_proof_state() -> None:
    catalog = _Catalog()
    service = ExtremeHealingEventRecordService(catalog=catalog)

    actual, critical = service.evaluate_pair(SimpleNamespace())

    assert actual.mechanic_complete is True
    assert critical.mechanic_complete is True
    assert actual.global_maximum_proven is False
    assert critical.global_maximum_proven is False


def test_heal_event_projection_rejects_unrelated_record_key() -> None:
    service = ExtremeHealingEventRecordService(catalog=_Catalog())

    with pytest.raises(ValueError, match="Unsupported healing-event Extreme record"):
        service.evaluate(SimpleNamespace(), "bash_damage")
