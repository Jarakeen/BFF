from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
)
from services.extreme_stealth_source_package_service import (
    ExtremeStealthSourcePackageService,
)


def _row(
    set_id: int,
    count: int,
    *,
    status: ExtremeGearSetObjectiveRelevance,
    delta: float,
    unresolved: tuple[str, ...] = (),
):
    return SimpleNamespace(
        set_id=set_id,
        piece_count=count,
        status=status,
        reviewed_delta=delta,
        candidate=SimpleNamespace(unresolved=unresolved),
    )


def _witness():
    return SimpleNamespace(
        set_ids=(10, 20, 30),
        counts=(3, 4, 5),
        set_names=("Night Terror", "Darloc", "Mystery"),
    )


def test_score_realization_sums_only_reviewed_complete_positive_stealth_sources() -> None:
    relevance = SimpleNamespace(
        evidence=(
            _row(
                10,
                3,
                status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                delta=2.0,
            ),
            _row(
                20,
                4,
                status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                delta=1.5,
            ),
            _row(
                30,
                5,
                status=ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT,
                delta=0.0,
            ),
        )
    )

    value, evidence, unresolved = ExtremeStealthSourcePackageService._score_realization(
        _witness(),
        relevance,
    )

    assert value == pytest.approx(3.5)
    assert evidence == (
        "Night Terror (3): 2 m reviewed detection-radius reduction",
        "Darloc (4): 1.5 m reviewed detection-radius reduction",
    )
    assert unresolved == ()


def test_score_realization_preserves_unresolved_candidate_without_crediting_amount() -> None:
    relevance = SimpleNamespace(
        evidence=(
            _row(
                10,
                3,
                status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                delta=2.0,
            ),
            _row(
                20,
                4,
                status=ExtremeGearSetObjectiveRelevance.UNRESOLVED,
                delta=9.0,
                unresolved=("Darloc stealth trigger unresolved",),
            ),
            _row(
                30,
                5,
                status=ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT,
                delta=0.0,
            ),
        )
    )

    value, evidence, unresolved = ExtremeStealthSourcePackageService._score_realization(
        _witness(),
        relevance,
    )

    assert value == pytest.approx(2.0)
    assert evidence == ("Night Terror (3): 2 m reviewed detection-radius reduction",)
    assert unresolved == ("Darloc stealth trigger unresolved",)


def test_missing_breakpoint_evidence_fails_open_for_proof_but_not_for_score() -> None:
    relevance = SimpleNamespace(
        evidence=(
            _row(
                10,
                3,
                status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                delta=2.0,
            ),
        )
    )

    value, evidence, unresolved = ExtremeStealthSourcePackageService._score_realization(
        _witness(),
        relevance,
    )

    assert value == pytest.approx(2.0)
    assert evidence == ("Night Terror (3): 2 m reviewed detection-radius reduction",)
    assert unresolved == (
        "Darloc (4): no stealth objective evidence",
        "Mystery (5): no stealth objective evidence",
    )
