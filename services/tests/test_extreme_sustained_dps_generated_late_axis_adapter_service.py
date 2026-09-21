from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
)
from services.extreme_sustained_dps_generated_late_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedLateAxisAdapterService,
)


class _FrontierService:
    def __init__(self, label, count=2, *, denominator_proven=True, unresolved=()):
        self.label = label
        self.count = count
        self.denominator_proven = denominator_proven
        self.unresolved = tuple(unresolved)

    def frontier(self, *args, **kwargs):
        return SimpleNamespace(
            candidate_count=self.count,
            denominator_proven=self.denominator_proven,
            unresolved=self.unresolved,
        )

    def candidate_at(self, *args, **kwargs):
        index = kwargs.get("index", args[-1] if args else 0)
        return SimpleNamespace(structural_index=index, label=f"{self.label}:{index}")


class _Assembly:
    @staticmethod
    def assemble(context, *, champion_points, potion, passive_ranks, skills):
        score = (
            champion_points.structural_index * 1000
            + potion.structural_index * 100
            + passive_ranks.structural_index * 10
            + skills.structural_index
        )
        return SimpleNamespace(
            coordinate=(
                champion_points.structural_index,
                potion.structural_index,
                passive_ranks.structural_index,
                skills.structural_index,
            ),
            score=float(score),
            context=context,
        )


def _context():
    return SimpleNamespace(
        build=SimpleNamespace(EsoClass="Arcanist"),
        progression=object(),
        front_skill_context=object(),
        back_skill_context=object(),
        one_bar_only=False,
    )


def test_adapts_four_canonical_late_frontiers_in_dependency_order() -> None:
    adapter = ExtremeSustainedDPSGeneratedLateAxisAdapterService(
        champion_points=_FrontierService("cp"),
        potions=_FrontierService("potion"),
        passive_ranks=_FrontierService("passive"),
        skill_bars=_FrontierService("skills"),
        assembly=_Assembly,
    )

    axes = adapter.axes()
    assert tuple(axis.name for axis in axes) == (
        "Champion Points",
        "Potion Family",
        "Passive Ranks",
        "Skill Bars",
    )

    state = adapter.root(_context())
    for axis in axes:
        assert axis.candidate_count(state) == 2
        state = axis.candidate_at(state, 1)

    assert state.complete is True
    assert state.assembled.coordinate == (1, 1, 1, 1)
    assert state.assembled.score == 1111.0


def test_runs_late_axis_product_through_lazy_branch_and_bound() -> None:
    adapter = ExtremeSustainedDPSGeneratedLateAxisAdapterService(
        champion_points=_FrontierService("cp"),
        potions=_FrontierService("potion"),
        passive_ranks=_FrontierService("passive"),
        skill_bars=_FrontierService("skills"),
        assembly=_Assembly,
    )

    def evaluate(node):
        assert node.state.complete
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=node.state.assembled.score,
            duration_seconds=10.0,
            mechanic_complete=True,
        )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        adapter.root(_context()),
        axes=adapter.axes(),
        evaluate_leaf=evaluate,
        required_duration_seconds=10.0,
    )

    assert result.evaluated_leaf_count == 16
    assert result.best_modeled_dps == 1111.0
    assert result.global_maximum_proven is True


def test_unresolved_frontier_fails_closed_before_candidate_materialization() -> None:
    adapter = ExtremeSustainedDPSGeneratedLateAxisAdapterService(
        champion_points=_FrontierService(
            "cp",
            denominator_proven=False,
            unresolved=("missing canonical CP identity",),
        ),
        potions=_FrontierService("potion"),
        passive_ranks=_FrontierService("passive"),
        skill_bars=_FrontierService("skills"),
        assembly=_Assembly,
    )

    with pytest.raises(ValueError, match="missing canonical CP identity"):
        adapter.axes()[0].candidate_count(adapter.root(_context()))


def test_skill_assembly_rejects_missing_prior_axis_selections() -> None:
    adapter = ExtremeSustainedDPSGeneratedLateAxisAdapterService(
        champion_points=_FrontierService("cp"),
        potions=_FrontierService("potion"),
        passive_ranks=_FrontierService("passive"),
        skill_bars=_FrontierService("skills"),
        assembly=_Assembly,
    )
    skill_axis = adapter.axes()[-1]

    with pytest.raises(ValueError, match="requires CP, potion, and passive"):
        skill_axis.candidate_at(adapter.root(_context()), 0)
