from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_mundus_food_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedMundusFoodAxisAdapterService,
)


def _context():
    return SimpleNamespace(build=PlayerBuild())


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
