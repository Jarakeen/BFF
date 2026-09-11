from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerComponentHealingResolution,
    RotationHealerPeriodicHealSeed,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicMagnitudePolicy,
    RotationHealerPeriodicRuntimeEvidence,
)


_DEMAND = RotationDemandWindow(
    name="runtime hot check",
    start_seconds=0.0,
    end_seconds=10.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=1,
)


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="runtime-hot",
        plan=RotationPlan(
            character_name="Healer",
            build_name="Runtime HoT",
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
            periodic_seeds=(
                RotationHealerPeriodicHealSeed(
                    time_seconds=0.0,
                    sequence=1,
                    source_name="Runtime HoT",
                    coefficient_number=2,
                    modeled_heal=100.0,
                ),
            ),
            delayed_seeds=(),
            unresolved=(),
        )

    def resolve_component_magnitude(self, **kwargs):
        self.component_calls.append(kwargs)
        return RotationHealerComponentHealingResolution(
            modeled_heal=float(kwargs["context"].modeled_heal),
        )


class _PeriodicTimingService:
    def inspect(self, build):
        return SimpleNamespace(
            entries=(
                SimpleNamespace(
                    skill_name="Runtime HoT",
                    coefficient_number=2,
                    timing="canonical-timing",
                ),
            ),
            unresolved=(),
        )


class _PeriodicRuntimeEvidenceService:
    def __init__(self, policy):
        self.policy = policy

    def resolve(self, **kwargs):
        return SimpleNamespace(
            runtime_evidence=RotationHealerPeriodicRuntimeEvidence(
                source_name="Runtime HoT",
                coefficient_number=2,
                duration_seconds=6.0,
                tick_interval_seconds=2.0,
                first_tick_offset_seconds=2.0,
                tick_on_expiry_boundary=True,
                magnitude_policy=self.policy,
            ),
            unresolved=(),
        )


class _DemandHealingService:
    def __init__(self):
        self.calls = []

    def assess(self, **kwargs):
        self.calls.append(kwargs)
        periodic = kwargs["periodic_projection"]
        modeled = sum(event.modeled_heal for event in periodic.events)
        return RotationHealerDemandHealingEvidence(
            demand=kwargs["demand"],
            direct_events=(),
            periodic_events=periodic.events,
            delayed_events=(),
            modeled_direct_healing=0.0,
            modeled_periodic_healing=modeled,
            modeled_delayed_healing=0.0,
            unresolved=periodic.unresolved,
        )


def _provider(policy):
    action = _ActionHealingService()
    demand = _DemandHealingService()
    provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=action,
        periodic_timing_service=_PeriodicTimingService(),
        periodic_runtime_evidence_service=_PeriodicRuntimeEvidenceService(policy),
        demand_healing_service=demand,
    )
    return provider, action, demand


def test_recalculate_each_tick_uses_exact_runtime_context_for_each_tick():
    provider, action, _ = _provider(
        RotationHealerPeriodicMagnitudePolicy.RECALCULATE_EACH_TICK
    )
    runtime_calls = []

    def runtime_context(time_seconds, sequence=None):
        runtime_calls.append((time_seconds, sequence))
        return SimpleNamespace(
            resolved=True,
            context=SimpleNamespace(modeled_heal=100.0 + time_seconds),
            active_bar="front",
            unresolved=(),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert [event.time_seconds for event in evidence.periodic_events] == [2.0, 4.0, 6.0]
    assert [event.modeled_heal for event in evidence.periodic_events] == [102.0, 104.0, 106.0]
    assert evidence.modeled_periodic_healing == pytest.approx(312.0)
    assert runtime_calls == [(2.0, 1000), (4.0, 1001), (6.0, 1002)]
    assert [call["context"].modeled_heal for call in action.component_calls] == [
        102.0,
        104.0,
        106.0,
    ]
    assert evidence.unresolved == ()


def test_snapshot_at_cast_keeps_cast_resolved_seed_magnitude():
    provider, action, _ = _provider(
        RotationHealerPeriodicMagnitudePolicy.SNAPSHOT_AT_CAST
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

    assert [event.modeled_heal for event in evidence.periodic_events] == [100.0, 100.0, 100.0]
    assert evidence.modeled_periodic_healing == pytest.approx(300.0)
    assert runtime_calls == []
    assert action.component_calls == []
    assert evidence.unresolved == ()


def test_recalculate_each_tick_fails_closed_when_tick_context_is_unresolved():
    provider, action, _ = _provider(
        RotationHealerPeriodicMagnitudePolicy.RECALCULATE_EACH_TICK
    )

    def runtime_context(time_seconds, sequence=None):
        return SimpleNamespace(
            resolved=False,
            context=None,
            active_bar="front",
            unresolved=("runtime potion state is unresolved",),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert evidence.periodic_events == ()
    assert evidence.modeled_periodic_healing == pytest.approx(0.0)
    assert action.component_calls == []
    assert any("runtime potion state is unresolved" in item for item in evidence.unresolved)
