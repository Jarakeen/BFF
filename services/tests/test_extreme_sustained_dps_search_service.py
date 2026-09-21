from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_search_service import ExtremeSustainedDPSSearchService


def _build(name: str) -> PlayerBuild:
    return PlayerBuild(Name="Tester", BuildName=name, Role="DD", BuildId=name)


class _Discovery:
    def __init__(self, candidates, exclusions=()):
        self.result = SimpleNamespace(
            candidates=tuple(candidates),
            exclusions=tuple(exclusions),
            candidate_count=len(tuple(candidates)),
            evidence=("discovery evidence",),
        )

    def discover(self):
        return self.result


class _Comparison:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def compare(self, builds, **kwargs):
        self.calls.append((tuple(build.BuildName for build in builds), kwargs))
        return self.result


def _candidate(name: str):
    return SimpleNamespace(build=_build(name), build_id=name, label=name)


def test_search_compares_all_discovered_candidates_under_same_scenario() -> None:
    comparison_result = SimpleNamespace(
        comparison_complete=True,
        leader=SimpleNamespace(label="B"),
        evidence=("comparison evidence",),
        unresolved=(),
    )
    comparison = _Comparison(comparison_result)
    service = ExtremeSustainedDPSSearchService(
        "data/eso.db",
        discovery=_Discovery((_candidate("A"), _candidate("B"))),
        comparison=comparison,
    )

    result = service.search(
        target_health=21_200_000,
        target_resistance=18200.0,
        target_name="Trial Dummy",
    )

    assert result.searched_candidate_count == 2
    assert result.search_complete_for_saved_denominator is True
    assert result.leader.label == "B"
    assert comparison.calls == [
        (
            ("A", "B"),
            {
                "target_health": 21_200_000,
                "target_resistance": 18200.0,
                "target_name": "Trial Dummy",
            },
        )
    ]
    assert any("no synthetic builds or rotations" in row for row in result.evidence)


def test_search_preserves_discovery_exclusions_and_comparison_gaps() -> None:
    exclusion = SimpleNamespace(
        label="Missing Rotation",
        reason="no saved canonical RotationPlan artifact",
    )
    comparison_result = SimpleNamespace(
        comparison_complete=False,
        leader=None,
        evidence=("comparison evidence",),
        unresolved=("Candidate execution horizons differ",),
    )
    service = ExtremeSustainedDPSSearchService(
        "data/eso.db",
        discovery=_Discovery(
            (_candidate("A"), _candidate("B")),
            exclusions=(exclusion,),
        ),
        comparison=_Comparison(comparison_result),
    )

    result = service.search(
        target_health=21_200_000,
        target_resistance=18200.0,
    )

    assert result.search_complete_for_saved_denominator is False
    assert any("Excluded Missing Rotation" in row for row in result.unresolved)
    assert "Candidate execution horizons differ" in result.unresolved


def test_search_requires_two_eligible_saved_candidates_before_comparison() -> None:
    comparison = _Comparison(SimpleNamespace())
    service = ExtremeSustainedDPSSearchService(
        "data/eso.db",
        discovery=_Discovery((_candidate("Only"),)),
        comparison=comparison,
    )

    result = service.search(
        target_health=21_200_000,
        target_resistance=18200.0,
    )

    assert result.comparison is None
    assert result.leader is None
    assert comparison.calls == []
    assert any("at least two eligible" in row for row in result.unresolved)
