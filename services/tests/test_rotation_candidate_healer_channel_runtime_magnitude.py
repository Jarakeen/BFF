from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from minmax.skill_component_classification import HealTemporalScope
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerChannelHealSeed,
    RotationHealerComponentHealingResolution,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelMagnitudePolicy,
    RotationHealerChannelRuntimeEvidence,
)


_DEMAND = RotationDemandWindow(
    name="channel demand",
    start_seconds=0.0,
    end_seconds=10.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=1,
)


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="channel-candidate",
        plan=RotationPlan(
            character_name="Healer",
            build_name="Channel Build",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _ActionHealingService:
    def __init__(self):
        self.component_calls = []

    def project(self, **kwargs):
        return RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(),
            delayed_seeds=(),
            channel_seeds=(
                RotationHealerChannelHealSeed(
                    time_seconds=1.0,
                    sequence=2,
                    source_name="Healing Channel",
                    coefficient_number=1,
                    modeled_heal=100.0,
                ),
            ),
            unresolved=(),
        )

    def resolve_component_magnitude(self, **kwargs):
        self.component_calls.append(kwargs)
        return RotationHealerComponentHealingResolution(
            modeled_heal=float(kwargs["context"].modeled_heal),
        )


def _provider(policy):
    action = _ActionHealingService()
    provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=action,
        channel_runtime_evidence=(
            RotationHealerChannelRuntimeEvidence(
                source_name="Healing Channel",
                coefficient_number=1,
                channel_duration_seconds=3.0,
                tick_interval_seconds=1.0,
                first_tick_offset_seconds=1.0,
                tick_on_channel_end_boundary=True,
                magnitude_policy=policy,
                provenance=("reviewed channel fixture",),
            ),
        ),
    )
    return provider, action


def test_recalculate_channel_ticks_use_exact_runtime_context_and_channel_scope():
    provider, action = _provider(
        RotationHealerChannelMagnitudePolicy.RECALCULATE_EACH_TICK
    )
    runtime_calls = []

    def runtime_context(time_seconds, sequence=None):
        runtime_calls.append((time_seconds, sequence))
        return SimpleNamespace(
            resolved=True,
            context=SimpleNamespace(modeled_heal=200.0 + time_seconds),
            active_bar="front",
            unresolved=(),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert [event.time_seconds for event in evidence.channel_events] == [2.0, 3.0, 4.0]
    assert [event.modeled_heal for event in evidence.channel_events] == [202.0, 203.0, 204.0]
    assert evidence.modeled_channel_healing == pytest.approx(609.0)
    assert evidence.modeled_total_healing == pytest.approx(609.0)
    assert runtime_calls == [(2.0, 2000), (3.0, 2001), (4.0, 2002)]
    assert [call["expected_temporal_scope"] for call in action.component_calls] == [
        HealTemporalScope.CHANNEL_TICK,
        HealTemporalScope.CHANNEL_TICK,
        HealTemporalScope.CHANNEL_TICK,
    ]
    assert evidence.unresolved == ()


def test_snapshot_channel_ticks_keep_cast_resolved_magnitude():
    provider, action = _provider(
        RotationHealerChannelMagnitudePolicy.SNAPSHOT_AT_CAST
    )
    runtime_calls = []

    def runtime_context(time_seconds, sequence=None):
        runtime_calls.append((time_seconds, sequence))
        return SimpleNamespace(
            resolved=True,
            context=SimpleNamespace(modeled_heal=999.0),
            active_bar="front",
            unresolved=(),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert [event.modeled_heal for event in evidence.channel_events] == [100.0, 100.0, 100.0]
    assert evidence.modeled_channel_healing == pytest.approx(300.0)
    assert runtime_calls == []
    assert action.component_calls == []
    assert evidence.unresolved == ()


def test_channel_tick_runtime_fails_closed_when_exact_context_is_unresolved():
    provider, action = _provider(
        RotationHealerChannelMagnitudePolicy.RECALCULATE_EACH_TICK
    )

    def runtime_context(time_seconds, sequence=None):
        return SimpleNamespace(
            resolved=False,
            context=None,
            active_bar="front",
            unresolved=("channel runtime state unavailable",),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert evidence.channel_events == ()
    assert evidence.modeled_channel_healing == pytest.approx(0.0)
    assert action.component_calls == []
    assert any("channel runtime state unavailable" in item for item in evidence.unresolved)
