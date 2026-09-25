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



def _candidate_runtime_resolver(
    *,
    event_proven=True,
    history_proven=True,
    runtime_effect_universe=object(),
    runtime_effect_scaling=object(),
):
    return SimpleNamespace(
        supplemental_event_denominator_proven=event_proven,
        supplemental_history_denominator_proven=history_proven,
        scenario_frontier=SimpleNamespace(
            runtime_effect_universe=runtime_effect_universe,
            runtime_effect_scaling=runtime_effect_scaling,
            weapon_poison_activation_service=object(),
            weapon_poison_consequence_resolver=object(),
        ),
    )

def test_ready_scenario_requires_closed_runtime_and_heavy_channel_evidence() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=_runtime(),
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is True
    assert result.blockers == ()


def test_missing_runtime_state_authority_blocks_theoretical_closure() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any(
        "runtime-state frontier or candidate-resolved runtime-state authority" in item
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



def test_candidate_runtime_state_authority_satisfies_preflight() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        candidate_runtime_state_resolver=_candidate_runtime_resolver(),
        candidate_runtime_state_resolver_present=True,
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is True
    assert result.blockers == ()
    assert any(
        "Candidate-resolved runtime-state authority is present" in row
        for row in result.evidence
    )


def test_candidate_runtime_state_authority_requires_closed_runtime_denominators() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        candidate_runtime_state_resolver=_candidate_runtime_resolver(
            event_proven=False,
            history_proven=False,
        ),
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any("runtime-event denominator" in item for item in result.blockers)
    assert any("runtime-history denominator" in item for item in result.blockers)


def test_candidate_runtime_state_authority_requires_canonical_effect_services() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        candidate_runtime_state_resolver=_candidate_runtime_resolver(
            runtime_effect_universe=None,
            runtime_effect_scaling=None,
        ),
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any("EffectVariant discovery" in item for item in result.blockers)
    assert any("effect scaling" in item for item in result.blockers)


def test_presence_flag_without_inspectable_candidate_runtime_authority_fails_closed() -> None:
    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        candidate_runtime_state_resolver_present=True,
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any("not inspectable" in item for item in result.blockers)

def test_candidate_runtime_state_authority_requires_weapon_poison_authorities() -> None:
    resolver = _candidate_runtime_resolver()
    resolver.scenario_frontier.weapon_poison_activation_service = None
    resolver.scenario_frontier.weapon_poison_consequence_resolver = None

    result = ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
        runtime_state_frontier=None,
        candidate_runtime_state_resolver=resolver,
        heavy_attack_channel_block_denominator_proven=True,
        encounter_policy_adapter=object(),
    )

    assert result.ready is False
    assert any("weapon-poison activation-event authority" in item for item in result.blockers)
    assert any("weapon-poison consequence authority" in item for item in result.blockers)



@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("candidate_runtime_state_resolver_present", "true"),
        ("heavy_attack_channel_block_denominator_proven", 1),
    ),
)
def test_preflight_requires_strict_boolean_top_level_flags(field, value) -> None:
    kwargs = {
        "runtime_state_frontier": _runtime(),
        "candidate_runtime_state_resolver_present": False,
        "heavy_attack_channel_block_denominator_proven": True,
        "encounter_policy_adapter": object(),
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match="must be boolean"):
        ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(**kwargs)


def test_preflight_rejects_truthy_non_boolean_runtime_frontier_proof() -> None:
    with pytest.raises(
        TypeError,
        match="runtime_state_frontier.denominator_proven must be boolean",
    ):
        ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
            runtime_state_frontier=_runtime(proven="true"),
            heavy_attack_channel_block_denominator_proven=True,
            encounter_policy_adapter=object(),
        )


def test_preflight_rejects_truthy_non_boolean_candidate_runtime_proofs() -> None:
    resolver = _candidate_runtime_resolver()
    resolver.supplemental_event_denominator_proven = "true"

    with pytest.raises(
        TypeError,
        match="supplemental_event_denominator_proven must be boolean",
    ):
        ExtremeSustainedDPSObjective32ScenarioPreflightService.assess(
            runtime_state_frontier=None,
            candidate_runtime_state_resolver=resolver,
            heavy_attack_channel_block_denominator_proven=True,
            encounter_policy_adapter=object(),
        )
