from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_objective32_scenario_preflight_service import (
    ExtremeSustainedDPSObjective32ScenarioPreflightService,
)


def _runtime(*, proven=True, unresolved=(), omitted_scope=()):
    return SimpleNamespace(
        denominator_proven=proven,
        unresolved=tuple(unresolved),
        omitted_scope=tuple(omitted_scope),
    )


def test_ready_scenario_requires_closed_runtime_and_heavy_channel_evidence() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=_runtime(),
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is True
    assert result.blockers == ()


def test_missing_runtime_state_frontier_blocks_theoretical_closure() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any(
        "requires an explicit runtime-state frontier" in item
        for item in result.blockers
    )


def test_open_or_omitted_runtime_scope_blocks_theoretical_closure() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=_runtime(
            proven=False,
            unresolved=("proc family unresolved",),
            omitted_scope=("cooldown offset family omitted",),
        ),
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any("not proven complete" in item for item in result.blockers)
    assert any("proc family unresolved" in item for item in result.blockers)
    assert any("cooldown offset family omitted" in item for item in result.blockers)


def test_open_heavy_channel_block_denominator_blocks_closure() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=_runtime(),
        heavy_attack_channel_block_denominator_proven=False,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any("channel-block denominator" in item for item in result.blockers)


def test_require_ready_raises_with_all_blockers() -> None:
    with pytest.raises(ValueError, match="scenario is not closure-ready"):
        ExtremeSustainedDPSObjective32ScenarioPreflightService.require_ready(
            runtime_state_frontier=None,
            heavy_attack_channel_block_denominator_proven=False,
            encounter_policy_adapter=None,
        )
