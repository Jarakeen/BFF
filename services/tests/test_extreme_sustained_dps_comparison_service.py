from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_comparison_service import (
    ExtremeSustainedDPSComparisonService,
)


class _Evaluator:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    def sustained_dps(
        self,
        build,
        *,
        target_health,
        target_resistance,
        target_name="Boss",
    ):
        self.calls.append(
            (
                build.BuildName,
                target_health,
                target_resistance,
                target_name,
            )
        )
        return self.rows.pop(0)


def _build(name: str) -> PlayerBuild:
    return PlayerBuild(
        Name="Damage Tester",
        BuildName=name,
        Role="DD",
    )


def _result(
    dps: float | None,
    *,
    duration: float = 60.0,
    complete: bool = True,
    unresolved=(),
):
    record = None
    if dps is not None:
        record = SimpleNamespace(
            modeled_dps=float(dps),
            duration_seconds=float(duration),
        )
    return SimpleNamespace(
        record=record,
        mechanic_complete=bool(complete),
        unresolved=tuple(unresolved),
    )


def test_compare_selects_unique_complete_leader_on_shared_horizon() -> None:
    evaluator = _Evaluator(
        (
            _result(120000.0),
            _result(130000.0),
            _result(125000.0),
        )
    )
    service = ExtremeSustainedDPSComparisonService(
        "data/eso.db",
        evaluator=evaluator,
    )

    result = service.compare(
        (_build("A"), _build("B"), _build("C")),
        target_health=21_200_000,
        target_resistance=18200.0,
        target_name="Trial Dummy",
    )

    assert result.comparison_complete is True
    assert result.leader is not None
    assert result.leader.label == "Damage Tester — B"
    assert result.leader.modeled_dps == pytest.approx(130000.0)
    assert [row.modeled_dps for row in result.ranked_candidates] == [
        130000.0,
        125000.0,
        120000.0,
    ]
    assert result.unresolved == ()
    assert evaluator.calls == [
        ("A", 21_200_000, 18200.0, "Trial Dummy"),
        ("B", 21_200_000, 18200.0, "Trial Dummy"),
        ("C", 21_200_000, 18200.0, "Trial Dummy"),
    ]


def test_compare_withholds_leader_when_any_candidate_is_mechanically_incomplete() -> None:
    service = ExtremeSustainedDPSComparisonService(
        "data/eso.db",
        evaluator=_Evaluator(
            (
                _result(130000.0),
                _result(
                    140000.0,
                    complete=False,
                    unresolved=("resource sustain unresolved",),
                ),
            )
        ),
    )

    result = service.compare(
        (_build("Stable"), _build("Questionable")),
        target_health=21_200_000,
        target_resistance=18200.0,
    )

    assert result.comparison_complete is False
    assert result.leader is None
    assert result.ranked_candidates[0].modeled_dps == pytest.approx(140000.0)
    assert any(
        "Questionable: resource sustain unresolved" in row
        for row in result.unresolved
    )


def test_compare_withholds_leader_when_execution_horizons_differ() -> None:
    service = ExtremeSustainedDPSComparisonService(
        "data/eso.db",
        evaluator=_Evaluator(
            (
                _result(140000.0, duration=20.0),
                _result(130000.0, duration=60.0),
            )
        ),
    )

    result = service.compare(
        (_build("Burst"), _build("Sustain")),
        target_health=21_200_000,
        target_resistance=18200.0,
    )

    assert result.comparison_complete is False
    assert result.leader is None
    assert "Candidate execution horizons differ" in result.unresolved[-1]


def test_compare_withholds_unique_leader_on_top_tie() -> None:
    service = ExtremeSustainedDPSComparisonService(
        "data/eso.db",
        evaluator=_Evaluator(
            (
                _result(130000.0),
                _result(130000.0),
            )
        ),
    )

    result = service.compare(
        (_build("One"), _build("Two")),
        target_health=21_200_000,
        target_resistance=18200.0,
    )

    assert result.comparison_complete is False
    assert result.leader is None
    assert any("tied" in row for row in result.unresolved)


def test_compare_requires_at_least_two_candidates() -> None:
    service = ExtremeSustainedDPSComparisonService(
        "data/eso.db",
        evaluator=_Evaluator((_result(130000.0),)),
    )

    with pytest.raises(ValueError, match="at least two candidates"):
        service.compare(
            (_build("Only"),),
            target_health=21_200_000,
            target_resistance=18200.0,
        )
