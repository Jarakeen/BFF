from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_dynamic_whole_plan_frontier_adapter_service import (
    ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService,
    ExtremeSustainedDPSIndexedWholePlanAdapter,
)


def test_rotation_seed_adapter_is_lazy_and_carries_dynamic_axes() -> None:
    class _Service:
        def frontier(self, candidate):
            return SimpleNamespace(
                candidate_count=4,
                denominator_proven=True,
            )

        def candidate_at(self, candidate, *, duration_seconds, index):
            return SimpleNamespace(index=index, duration=duration_seconds)

    adapter = ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService.rotation_seed(
        _Service(),
        object(),
        duration_seconds=20.0,
    )

    assert adapter.axes == ("rotation_order", "light_attack_weave")
    assert adapter.choice_count == 4
    assert adapter.choice_at(3).index == 3


def test_anchored_policy_adapter_preserves_open_continuous_timing_scope() -> None:
    class _Service:
        def frontier(self, **kwargs):
            return SimpleNamespace(
                candidate_count=6,
                anchored_policy_denominator_proven=True,
                continuous_potion_timing_closed=False,
                delayed_ultimate_timing_closed=False,
            )

        def candidate_at(self, **kwargs):
            return SimpleNamespace(index=kwargs["index"])

    adapter = ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService.anchored_ultimate_potion(
        _Service(),
        build=object(),
        seed=object(),
        potion_cooldown_seconds=45.0,
        starting_ultimate=0.0,
    )

    assert adapter.axes == ("ultimate_policy", "potion_timing_policy")
    assert adapter.choice_count == 6
    assert len(adapter.omitted_scope) == 2
    assert adapter.choice_at(5).index == 5


def test_execute_policy_adapter_preserves_frontier_denominator() -> None:
    rows = (object(), object())
    adapter = ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService.execute_policy(
        SimpleNamespace(
            candidates=rows,
            denominator_proven=True,
            omitted_scope=(),
        )
    )

    assert adapter.axes == ("execute_policy",)
    assert adapter.choice_count == 2
    assert adapter.choice_at(1) is rows[1]


def test_heavy_attack_adapter_preserves_reviewed_window_omission() -> None:
    rows = (object(),)
    adapter = ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService.heavy_attack_policy(
        SimpleNamespace(
            candidates=rows,
            denominator_proven=True,
            omitted_scope=(),
        )
    )

    assert adapter.axes == ("heavy_attack_policy",)
    assert adapter.choice_count == 1
    assert any("caller-reviewed safe set" in row for row in adapter.omitted_scope)


def test_indexed_whole_plan_adapter_rejects_out_of_range_index() -> None:
    rows = (object(),)
    adapter = ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService.execute_policy(
        SimpleNamespace(candidates=rows, denominator_proven=True)
    )

    try:
        adapter.choice_at(1)
    except IndexError:
        pass
    else:
        raise AssertionError("expected out-of-range dynamic choice to fail")



def test_heavy_attack_adapter_can_clear_omission_with_complete_window_proof() -> None:
    rows = (object(), object())
    adapter = ExtremeSustainedDPSDynamicWholePlanFrontierAdapterService.heavy_attack_policy(
        SimpleNamespace(
            candidates=rows,
            denominator_proven=True,
            omitted_scope=(),
        ),
        complete_window_denominator_proven=True,
    )

    assert adapter.axes == ("heavy_attack_policy",)
    assert adapter.choice_count == 2
    assert adapter.omitted_scope == ()


def test_indexed_whole_plan_adapter_requires_strict_proof_record_fields() -> None:
    with pytest.raises(TypeError, match="axes must be a tuple"):
        ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=["execute_policy"],  # type: ignore[arg-type]
            choice_count=1,
            _resolver=lambda _index: object(),
            denominator_proven=True,
            omitted_scope=(),
        )

    with pytest.raises(TypeError, match="choice_count must be an integer"):
        ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("execute_policy",),
            choice_count=True,  # type: ignore[arg-type]
            _resolver=lambda _index: object(),
            denominator_proven=True,
            omitted_scope=(),
        )

    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("execute_policy",),
            choice_count=1,
            _resolver=lambda _index: object(),
            denominator_proven="true",  # type: ignore[arg-type]
            omitted_scope=(),
        )

    with pytest.raises(TypeError, match="omitted_scope must be a tuple"):
        ExtremeSustainedDPSIndexedWholePlanAdapter(
            axes=("execute_policy",),
            choice_count=1,
            _resolver=lambda _index: object(),
            denominator_proven=True,
            omitted_scope=["open"],  # type: ignore[arg-type]
        )


def test_indexed_whole_plan_adapter_rejects_boolean_index() -> None:
    adapter = ExtremeSustainedDPSIndexedWholePlanAdapter(
        axes=("execute_policy",),
        choice_count=1,
        _resolver=lambda index: index,
        denominator_proven=True,
        omitted_scope=(),
    )

    with pytest.raises(TypeError, match="index must be an integer"):
        adapter.choice_at(True)
