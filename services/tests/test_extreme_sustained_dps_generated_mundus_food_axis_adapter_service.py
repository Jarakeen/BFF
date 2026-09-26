from __future__ import annotations

from dataclasses import dataclass

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_mundus_food_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService,
)


@dataclass(frozen=True)
class _Context:
    build: PlayerBuild


def _context():
    return _Context(build=PlayerBuild())


def test_generated_mundus_food_axes_mutate_exact_build_state_in_order() -> None:
    service = ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService(
        mundus_choices=("The Thief", "The Lover"),
        food_choices=("Food B", "Food A"),
        denominator_proven=True,
    )
    state = service.root(_context())
    mundus_axis, food_axis = service.axes()

    assert mundus_axis.candidate_count(state) == 2
    state = mundus_axis.candidate_at(state, 1)
    assert state.context.build.Mundus == "The Thief"
    assert state.complete is False

    assert food_axis.candidate_count(state) == 2
    state = food_axis.candidate_at(state, 0)
    assert state.context.build.Mundus == "The Thief"
    assert state.context.build.Food == "Food A"
    assert state.complete is True
    assert service.coverage().dominated_axes == ("mundus", "food")


def test_food_axis_requires_mundus_selection() -> None:
    service = ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService(
        mundus_choices=("The Thief",),
        food_choices=("Food A",),
        denominator_proven=True,
    )
    state = service.root(_context())

    with pytest.raises(ValueError, match="selected Mundus"):
        service.axes()[1].candidate_count(state)


def test_unproven_mundus_food_denominator_fails_closed() -> None:
    service = ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService(
        mundus_choices=("The Thief",),
        food_choices=("Food A",),
        denominator_proven=False,
    )

    with pytest.raises(ValueError, match="proven finite denominator"):
        service.axes()[0].candidate_count(service.root(_context()))

    assert service.coverage().dominated_axes == ()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("mundus_choices", ["The Thief"], "Mundus choices must be a tuple"),
        ("food_choices", ["Food A"], "food choices must be a tuple"),
        ("denominator_proven", "true", "denominator_proven must be boolean"),
        ("unresolved", ["open"], "unresolved must be a tuple"),
    ),
)
def test_generated_mundus_food_constructor_rejects_mutable_or_truthy_proof_inputs(
    field,
    value,
    message,
) -> None:
    kwargs = {
        "mundus_choices": ("The Thief",),
        "food_choices": ("Food A",),
        "denominator_proven": True,
        "unresolved": (),
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=message):
        ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService(**kwargs)


def test_generated_mundus_food_axes_reject_boolean_indices() -> None:
    service = ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService(
        mundus_choices=("The Thief",),
        food_choices=("Food A",),
        denominator_proven=True,
    )
    state = service.root(_context())
    mundus_axis, food_axis = service.axes()

    with pytest.raises(TypeError, match="Mundus choice index must be an integer"):
        mundus_axis.candidate_at(state, True)

    state = mundus_axis.candidate_at(state, 0)
    with pytest.raises(TypeError, match="food choice index must be an integer"):
        food_axis.candidate_at(state, False)
