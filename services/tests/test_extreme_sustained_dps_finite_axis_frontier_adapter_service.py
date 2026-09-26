from __future__ import annotations

import pytest

from types import SimpleNamespace

from services.extreme_sustained_dps_finite_axis_frontier_adapter_service import (
    ExtremeSustainedDPSFiniteAxisFrontierAdapterService,
)


class _CPService:
    def frontier(self):
        return SimpleNamespace(
            candidate_count=3,
            denominator_proven=True,
            evidence=("cp",),
            unresolved=(),
        )

    def candidate_at(self, baseline_build, index):
        return SimpleNamespace(structural_index=index, build=baseline_build)


class _PassiveService:
    def frontier(self, progression, *, character_class):
        return SimpleNamespace(
            candidate_count=2,
            denominator_proven=True,
            evidence=("passive",),
            unresolved=(),
        )

    def candidate_at(self, progression, *, character_class, index):
        return SimpleNamespace(structural_index=index, progression=progression)


def test_cp_adapter_is_indexed_and_lazy() -> None:
    build = object()
    adapter = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
        _CPService(),
        build,
    )

    assert adapter.axes == ("champion_points",)
    assert adapter.choice_count == 3
    assert adapter.denominator_proven is True
    choice = adapter.choice_at(2)
    assert choice.choice_id == "cp:2"
    assert choice.payload.structural_index == 2


def test_passive_adapter_preserves_passive_axis_only() -> None:
    progression = object()
    adapter = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.passive_ranks(
        _PassiveService(),
        progression,
        character_class="warden",
    )

    assert adapter.axes == ("passive_ranks",)
    assert adapter.choice_count == 2
    assert adapter.choice_at(1).choice_id == "passive:1"


def test_dual_bar_gear_adapter_exposes_exact_catalog_states() -> None:
    states = (object(), object(), object())
    frontier = SimpleNamespace(
        catalog=SimpleNamespace(states=states),
        denominator_proven=True,
        evidence=("gear",),
        unresolved=(),
    )
    adapter = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.dual_bar_gear(frontier)

    assert adapter.axes == ("gear_topology", "named_gear_realization")
    assert adapter.choice_count == 3
    assert adapter.choice_at(1).choice_id == "gear:1"
    assert adapter.choice_at(1).payload is states[1]


def test_incomplete_source_frontier_remains_incomplete() -> None:
    frontier = SimpleNamespace(
        catalog=SimpleNamespace(states=(object(),)),
        denominator_proven=False,
        evidence=(),
        unresolved=("gear denominator unresolved",),
    )
    adapter = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.dual_bar_gear(frontier)

    assert adapter.denominator_proven is False
    assert adapter.unresolved == ("gear denominator unresolved",)


def test_adapter_rejects_out_of_range_index() -> None:
    adapter = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
        _CPService(),
        object(),
    )

    try:
        adapter.choice_at(3)
    except IndexError:
        pass
    else:
        raise AssertionError("expected out-of-range indexed choice to raise")


def test_adapter_rejects_boolean_index() -> None:
    adapter = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
        _CPService(),
        object(),
    )

    with pytest.raises(TypeError, match="choice index must be an integer"):
        adapter.choice_at(True)


def test_adapter_rejects_truthy_denominator_and_boolean_count() -> None:
    class _BadProofService(_CPService):
        def frontier(self):
            return SimpleNamespace(
                candidate_count=1,
                denominator_proven="true",
                evidence=("cp",),
                unresolved=(),
            )

    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
            _BadProofService(),
            object(),
        )

    class _BadCountService(_CPService):
        def frontier(self):
            return SimpleNamespace(
                candidate_count=True,
                denominator_proven=True,
                evidence=("cp",),
                unresolved=(),
            )

    with pytest.raises(TypeError, match="choice_count must be an integer"):
        ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
            _BadCountService(),
            object(),
        )


def test_adapter_rejects_non_tuple_evidence_shape() -> None:
    class _BadEvidenceService(_CPService):
        def frontier(self):
            return SimpleNamespace(
                candidate_count=1,
                denominator_proven=True,
                evidence=["cp"],
                unresolved=(),
            )

    with pytest.raises(TypeError, match="evidence must be a tuple"):
        ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
            _BadEvidenceService(),
            object(),
        )
