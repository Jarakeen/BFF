from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_global_generated_search_service import (
    ExtremeSustainedDPSGlobalGeneratedSearchService,
)


@dataclass(frozen=True)
class _PipelineState:
    family: int
    selected: int | None = None

    @property
    def complete(self):
        return self.selected is not None


class _Families:
    def validate_denominator(self):
        return SimpleNamespace(
            denominator_proven=True,
            choice_count=2,
            unresolved=(),
        )

    def choice_at(self, index):
        return SimpleNamespace(structural_family_index=index)


class _Materialization:
    def materialize(self, choice):
        return SimpleNamespace(
            complete=True,
            build=f"build-{choice.structural_family_index}",
            progression=f"progression-{choice.structural_family_index}",
            unresolved=(),
        )


class _Pipeline:
    def __init__(self):
        self.root_calls = []

    def root(self, build, progression, **kwargs):
        family = int(str(build).split("-")[-1])
        self.root_calls.append((build, progression, kwargs))
        return _PipelineState(family=family)

    @staticmethod
    def axes():
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Choice",
                candidate_count=lambda _state: 2,
                candidate_at=lambda state, index: replace(
                    state,
                    selected=index,
                ),
            ),
        )


class _Leaf:
    def evaluator(self, **_kwargs):
        def evaluate(node):
            score = float(node.state.family * 10 + node.state.selected)
            return ExtremeSustainedDPSExactLeafEvaluation(
                candidate_key=node.candidate_key,
                modeled_dps=score,
                duration_seconds=20.0,
                mechanic_complete=True,
            )

        return evaluate


def test_global_search_prepends_structural_family_to_pipeline_axes() -> None:
    pipeline = _Pipeline()
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=pipeline,
        leaf_evaluation=_Leaf(),
    )

    result = service.search(
        dual_bar_frontier="gear-frontier",
        candidate_id_prefix="objective32",
        required_duration_seconds=20.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="Boss",
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
    )

    assert result.evaluated_leaf_count == 4
    assert result.best_modeled_dps == 11.0
    assert result.global_maximum_proven is True
    assert len(pipeline.root_calls) == 2
    assert pipeline.root_calls[0][0] == "build-0"
    assert pipeline.root_calls[1][0] == "build-1"
    assert pipeline.root_calls[0][2]["dual_bar_frontier"] == "gear-frontier"


def test_global_search_refuses_unproven_structural_denominator() -> None:
    class _OpenFamilies(_Families):
        def validate_denominator(self):
            return SimpleNamespace(
                denominator_proven=False,
                choice_count=2,
                unresolved=("pair mismatch",),
            )

    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_OpenFamilies(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )

    try:
        service.search(
            dual_bar_frontier="gear-frontier",
            candidate_id_prefix="objective32",
            required_duration_seconds=20.0,
            potion_cooldown_seconds=45.0,
            starting_ultimate=0.0,
            priorities="priorities",
            snapshot_resolver="resolver",
            target_identity="Boss",
            runtime_snapshot="snapshot",
            target_health=1_000_000,
            target_resistance=18_200.0,
        )
    except ValueError as exc:
        assert "proven structural family denominator" in str(exc)
    else:
        raise AssertionError("unproven structural denominator should fail closed")
