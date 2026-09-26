from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_generated_gear_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedGearAxisAdapterService,
)


@dataclass(frozen=True)
class _Build:
    steps: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Context:
    build: _Build


class _ContextService:
    @staticmethod
    def compose(build, progression, *, gear_state):
        return _Context(build=replace(build, steps=(*build.steps, gear_state)))


class _MutationFrontier:
    def __init__(self, label, *, proven=True, unresolved=()):
        self.label = label
        self.proven = proven
        self.unresolved = tuple(unresolved)

    def frontier(self, build):
        return SimpleNamespace(
            candidate_count=2,
            denominator_proven=self.proven,
            unresolved=self.unresolved,
        )

    def candidate_at(self, build, index):
        return SimpleNamespace(
            structural_index=index,
            build=replace(build, steps=(*build.steps, f"{self.label}:{index}")),
        )


def _dual_frontier(*, proven=True, unresolved=()):
    return SimpleNamespace(
        dual_bar_state_count=2,
        denominator_proven=proven,
        unresolved=tuple(unresolved),
        catalog=SimpleNamespace(states=("gear:0", "gear:1")),
    )


def _adapter():
    return ExtremeSustainedDPSGeneratedGearAxisAdapterService(
        context_service=_ContextService(),
        armor=_MutationFrontier("armor"),
        jewelry=_MutationFrontier("jewelry"),
        weapon=_MutationFrontier("weapon"),
    )


def test_gear_axes_mutate_one_evolving_build_without_erasing_prior_choices() -> None:
    adapter = _adapter()
    axes = adapter.axes()
    assert tuple(axis.name for axis in axes) == (
        "Dual Bar Gear",
        "Armor Traits and Enchants",
        "Jewelry Traits and Enchants",
        "Weapon Traits and Enchants",
    )

    state = adapter.root(
        _Build(),
        object(),
        dual_bar_frontier=_dual_frontier(),
    )
    for axis in axes:
        assert axis.candidate_count(state) == 2
        state = axis.candidate_at(state, 1)

    assert state.complete is True
    assert state.current_build.steps == (
        "gear:1",
        "armor:1",
        "jewelry:1",
        "weapon:1",
    )


def test_trait_axis_cannot_run_before_dual_bar_gear_selection() -> None:
    adapter = _adapter()
    state = adapter.root(
        _Build(),
        object(),
        dual_bar_frontier=_dual_frontier(),
    )

    with pytest.raises(ValueError, match="selected dual-bar gear state"):
        adapter.axes()[1].candidate_count(state)


def test_unproven_dual_bar_denominator_fails_closed() -> None:
    adapter = _adapter()
    state = adapter.root(
        _Build(),
        object(),
        dual_bar_frontier=_dual_frontier(
            proven=False,
            unresolved=("topology branch missing",),
        ),
    )

    with pytest.raises(ValueError, match="topology branch missing"):
        adapter.axes()[0].candidate_count(state)


def test_unresolved_downstream_trait_frontier_fails_closed() -> None:
    adapter = ExtremeSustainedDPSGeneratedGearAxisAdapterService(
        context_service=_ContextService(),
        armor=_MutationFrontier(
            "armor",
            proven=False,
            unresolved=("armor glyph denominator missing",),
        ),
        jewelry=_MutationFrontier("jewelry"),
        weapon=_MutationFrontier("weapon"),
    )
    state = adapter.root(
        _Build(),
        object(),
        dual_bar_frontier=_dual_frontier(),
    )
    state = adapter.axes()[0].candidate_at(state, 0)

    with pytest.raises(ValueError, match="armor glyph denominator missing"):
        adapter.axes()[1].candidate_count(state)


def test_truthy_non_boolean_gear_denominator_proof_fails_closed() -> None:
    adapter = _adapter()
    frontier = _dual_frontier()
    frontier.denominator_proven = "false"
    state = adapter.root(_Build(), object(), dual_bar_frontier=frontier)

    with pytest.raises(TypeError, match="proof flag must be boolean"):
        adapter.axes()[0].candidate_count(state)


def test_boolean_gear_candidate_count_is_not_accepted_as_integer() -> None:
    adapter = _adapter()
    frontier = _dual_frontier()
    frontier.dual_bar_state_count = True
    state = adapter.root(_Build(), object(), dual_bar_frontier=frontier)

    with pytest.raises(TypeError, match="candidate count must be an integer"):
        adapter.axes()[0].candidate_count(state)
