from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_combat_dynamic_axis_coverage_service import (
    ExtremeSustainedDPSCombatDynamicAxisCoverageService,
)


def test_complete_skill_bar_frontier_promotes_skill_bars_axis() -> None:
    result = ExtremeSustainedDPSCombatDynamicAxisCoverageService.skill_bars(
        SimpleNamespace(
            front_candidate_count=10,
            back_candidate_count=10,
            candidate_count=100,
            denominator_proven=True,
            unresolved=(),
        )
    )

    assert result.proof.dominated_axes == ("skill_bars",)
    assert result.omitted_scope == ()


def test_complete_seed_rotation_promotes_order_and_weave_only() -> None:
    result = ExtremeSustainedDPSCombatDynamicAxisCoverageService.rotation_seed_family(
        SimpleNamespace(
            candidate_count=57600,
            front_order_count=120,
            back_order_count=120,
            starting_route_count=2,
            weave_state_count=2,
            denominator_proven=True,
            unresolved=(),
        )
    )

    assert result.proof.dominated_axes == (
        "rotation_order",
        "light_attack_weave",
    )
    assert result.omitted_scope == ()
    assert result.proof.omitted_scope == ()
    assert any("separate canonical axes" in row for row in result.evidence)


def test_anchored_policy_promotes_finite_family_but_preserves_continuous_omission() -> None:
    result = ExtremeSustainedDPSCombatDynamicAxisCoverageService.anchored_ultimate_potion_policy(
        SimpleNamespace(
            ultimate_options=("none", "front"),
            potion_policies=(object(), object(), object()),
            candidate_count=6,
            anchored_policy_denominator_proven=True,
            continuous_potion_timing_closed=False,
            delayed_ultimate_timing_closed=False,
            unresolved=(),
        )
    )

    assert result.proof.dominated_axes == (
        "ultimate_policy",
        "potion_timing_policy",
    )
    assert len(result.omitted_scope) == 2
    assert result.proof.omitted_scope == result.omitted_scope
    assert any("continuous potion" in row for row in result.omitted_scope)
    assert any("Ultimate delay" in row for row in result.omitted_scope)


def test_incomplete_execute_frontier_promotes_nothing() -> None:
    result = ExtremeSustainedDPSCombatDynamicAxisCoverageService.execute_policy(
        SimpleNamespace(
            candidates=(object(),),
            denominator_proven=False,
            unresolved=("execute runtime state unresolved",),
        )
    )

    assert result.proof.dominated_axes == ()
    assert "execute runtime state unresolved" in result.unresolved


def test_complete_heavy_policy_promotes_only_reviewed_window_family() -> None:
    result = ExtremeSustainedDPSCombatDynamicAxisCoverageService.heavy_attack_policy(
        SimpleNamespace(
            candidates=(object(), object()),
            denominator_proven=True,
            unresolved=(),
        )
    )

    assert result.proof.dominated_axes == ("heavy_attack_policy",)
    assert result.proof.omitted_scope == result.omitted_scope
    assert any("caller-supplied reviewed safe set" in row for row in result.omitted_scope)



def test_complete_discovered_heavy_policy_clears_reviewed_window_omission() -> None:
    result = ExtremeSustainedDPSCombatDynamicAxisCoverageService.heavy_attack_policy(
        SimpleNamespace(
            candidates=(object(), object()),
            denominator_proven=True,
            unresolved=(),
        ),
        complete_window_denominator_proven=True,
    )

    assert result.proof.dominated_axes == ("heavy_attack_policy",)
    assert result.omitted_scope == ()
    assert result.proof.omitted_scope == ()
    assert any(
        "proven-complete scheduler-derived Heavy Attack start family" in row
        for row in result.evidence
    )


def test_dynamic_axis_coverage_rejects_mutable_unresolved_evidence() -> None:
    with pytest.raises(TypeError, match="unresolved evidence must be a tuple"):
        ExtremeSustainedDPSCombatDynamicAxisCoverageService.execute_policy(
            SimpleNamespace(
                candidates=(),
                denominator_proven=True,
                unresolved=[],
            )
        )


def test_dynamic_axis_coverage_requires_strict_denominator_proof() -> None:
    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSCombatDynamicAxisCoverageService.execute_policy(
            SimpleNamespace(
                candidates=(),
                denominator_proven=1,
                unresolved=(),
            )
        )


def test_anchored_dynamic_axis_coverage_requires_strict_timing_closure_flags() -> None:
    frontier = SimpleNamespace(
        ultimate_options=(),
        potion_policies=(),
        candidate_count=0,
        anchored_policy_denominator_proven=True,
        continuous_potion_timing_closed="false",
        delayed_ultimate_timing_closed=False,
        unresolved=(),
    )
    with pytest.raises(TypeError, match="continuous_potion_timing_closed must be boolean"):
        ExtremeSustainedDPSCombatDynamicAxisCoverageService.anchored_ultimate_potion_policy(
            frontier
        )


def test_heavy_attack_dynamic_axis_coverage_requires_strict_window_proof() -> None:
    with pytest.raises(TypeError, match="complete-window denominator proof must be boolean"):
        ExtremeSustainedDPSCombatDynamicAxisCoverageService.heavy_attack_policy(
            SimpleNamespace(
                candidates=(),
                denominator_proven=True,
                unresolved=(),
            ),
            complete_window_denominator_proven=1,  # type: ignore[arg-type]
        )
