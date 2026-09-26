from __future__ import annotations

from dataclasses import dataclass, replace

import pytest
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
        heavy_attack_channel_blocks=("channel-block",),
        heavy_attack_channel_block_denominator_proven=True,
    )

    assert result.evaluated_leaf_count == 4
    assert result.best_modeled_dps == 11.0
    assert result.global_maximum_proven is True
    assert len(pipeline.root_calls) == 2
    assert pipeline.root_calls[0][0] == "build-0"
    assert pipeline.root_calls[1][0] == "build-1"
    assert pipeline.root_calls[0][2]["dual_bar_frontier"] == "gear-frontier"
    assert pipeline.root_calls[0][2]["heavy_attack_channel_blocks"] == (
        "channel-block",
    )
    assert (
        pipeline.root_calls[0][2][
            "heavy_attack_channel_block_denominator_proven"
        ]
        is True
    )


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



def test_global_search_reports_structural_and_pipeline_axis_inventory() -> None:
    class _TaggedPipeline(_Pipeline):
        @staticmethod
        def axes():
            return (
                ExtremeSustainedDPSIndexedFrontierAxis(
                    "Choice",
                    candidate_count=lambda _state: 1,
                    candidate_at=lambda state, _index: replace(
                        state,
                        selected=0,
                    ),
                    canonical_axes=("champion_points",),
                ),
            )

    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_TaggedPipeline(),
        leaf_evaluation=_Leaf(),
    )

    inventory = service.axis_inventory()

    assert {
        "race",
        "class_route",
        "attributes",
        "champion_points",
    }.issubset(set(inventory.searched_canonical_axes))
    assert "encounter_policy" in inventory.missing_canonical_axes



def test_global_search_rejects_static_runtime_state_when_pipeline_resolves_candidates() -> None:
    pipeline = _Pipeline()
    pipeline.runtime_state_frontier_resolver = object()
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=pipeline,
        leaf_evaluation=_Leaf(),
    )

    with pytest.raises(ValueError, match="cannot combine pipeline candidate-resolved"):
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
            runtime_state_frontier=object(),
        )



def test_axis_inventory_uses_pipeline_candidate_runtime_state_without_search_inputs() -> None:
    class _RuntimePipeline(_Pipeline):
        runtime_state_frontier_resolver = object()

        @staticmethod
        def axes():
            return (
                ExtremeSustainedDPSIndexedFrontierAxis(
                    "Runtime State",
                    candidate_count=lambda _state: 1,
                    candidate_at=lambda state, _index: state,
                    canonical_axes=("runtime_state",),
                ),
            )

    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_RuntimePipeline(),
        leaf_evaluation=_Leaf(),
    )

    inventory = service.axis_inventory()

    assert "runtime_state" in inventory.searched_canonical_axes


def _valid_search_kwargs():
    return {
        "dual_bar_frontier": "gear-frontier",
        "candidate_id_prefix": "objective32",
        "required_duration_seconds": 20.0,
        "potion_cooldown_seconds": 45.0,
        "starting_ultimate": 0.0,
        "priorities": "priorities",
        "snapshot_resolver": "resolver",
        "target_identity": "Boss",
        "runtime_snapshot": "snapshot",
        "target_health": 1_000_000,
        "target_resistance": 18_200.0,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("use_scheduled_combat_attacks_for_ultimate", "false"),
        ("heavy_attack_channel_block_denominator_proven", 1),
    ),
)
def test_global_search_requires_strict_boolean_proof_inputs(field, value) -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )
    kwargs = _valid_search_kwargs()
    kwargs[field] = value

    with pytest.raises(TypeError, match="must be boolean"):
        service.search(**kwargs)


@pytest.mark.parametrize("duration", (0.0, -1.0))
def test_global_search_requires_positive_duration(duration) -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )
    kwargs = _valid_search_kwargs()
    kwargs["required_duration_seconds"] = duration

    with pytest.raises(ValueError, match="required_duration_seconds must be positive"):
        service.search(**kwargs)


def test_global_search_rejects_invalid_initial_bar() -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )
    kwargs = _valid_search_kwargs()
    kwargs["initial_bar"] = "middle"

    with pytest.raises(ValueError, match="initial_bar must be 'front' or 'back'"):
        service.search(**kwargs)



@pytest.mark.parametrize(
    "field",
    (
        "ultimate_generation_events",
        "heroism_windows",
        "duration_rules",
        "heavy_attack_windows",
        "heavy_attack_channel_blocks",
    ),
)
def test_global_search_rejects_mutable_frontier_collections(field) -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )
    kwargs = _valid_search_kwargs()
    kwargs[field] = []

    with pytest.raises(TypeError, match=f"{field} must be a tuple"):
        service.search(**kwargs)



@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("denominator_proven", "true", "denominator proof must be boolean"),
        ("unresolved", [], "unresolved evidence must be a tuple"),
        ("choice_count", True, "choice_count must be an integer"),
        ("choice_count", -1, "choice_count must be non-negative"),
        ("choice_count", 0, "proven structural family denominator cannot be empty"),
    ),
)
def test_global_search_rejects_malformed_structural_denominator(field, value, message) -> None:
    class _MalformedFamilies(_Families):
        def validate_denominator(self):
            values = {
                "denominator_proven": True,
                "choice_count": 2,
                "unresolved": (),
            }
            values[field] = value
            return SimpleNamespace(**values)

    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_MalformedFamilies(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )

    with pytest.raises((TypeError, ValueError), match=message):
        service.search(**_valid_search_kwargs())


@pytest.mark.parametrize(
    ("complete", "unresolved", "message"),
    (
        ("true", (), "complete flag must be boolean"),
        (True, [], "unresolved evidence must be a tuple"),
    ),
)
def test_global_search_rejects_malformed_structural_materialization(
    complete, unresolved, message
) -> None:
    class _MalformedMaterialization(_Materialization):
        def materialize(self, choice):
            row = super().materialize(choice)
            return SimpleNamespace(
                complete=complete,
                build=row.build,
                progression=row.progression,
                unresolved=unresolved,
            )

    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_MalformedMaterialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )

    with pytest.raises(TypeError, match=message):
        service.search(**_valid_search_kwargs())


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("required_duration_seconds", "20", "required_duration_seconds must be numeric"),
        ("target_resistance", "18200", "target_resistance must be numeric"),
        ("starting_ultimate", "0", "starting_ultimate must be numeric"),
        ("potion_cooldown_seconds", "45", "potion_cooldown_seconds must be numeric"),
    ),
)
def test_global_search_rejects_coerced_numeric_scalars(field, value, match) -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )
    kwargs = _valid_search_kwargs()
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        service.search(**kwargs)


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("candidate_id_prefix", 7, "candidate_id_prefix must be a string"),
        ("target_identity", "", "target_identity must be a non-empty string"),
        ("target_name", None, "target_name must be a non-empty string"),
        ("initial_bar", 1, "initial_bar must be a string"),
    ),
)
def test_global_search_requires_typed_identity_strings(field, value, match) -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )
    kwargs = _valid_search_kwargs()
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=match):
        service.search(**kwargs)


def test_global_search_rejects_negative_starting_ultimate_and_nonpositive_potion_cooldown() -> None:
    service = ExtremeSustainedDPSGlobalGeneratedSearchService(
        structural_families=_Families(),
        structural_materialization=_Materialization(),
        pipeline=_Pipeline(),
        leaf_evaluation=_Leaf(),
    )

    kwargs = _valid_search_kwargs()
    kwargs["starting_ultimate"] = -1.0
    with pytest.raises(ValueError, match="starting_ultimate must be non-negative"):
        service.search(**kwargs)

    kwargs = _valid_search_kwargs()
    kwargs["potion_cooldown_seconds"] = 0.0
    with pytest.raises(ValueError, match="potion_cooldown_seconds must be positive"):
        service.search(**kwargs)
