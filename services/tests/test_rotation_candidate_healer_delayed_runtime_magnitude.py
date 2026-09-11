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
    RotationHealerDelayedHealSeed,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedMagnitudePolicy,
    RotationHealerDelayedRuntimeEvidence,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)


_DEMAND = RotationDemandWindow(
    name="runtime delayed check",
    start_seconds=0.0,
    end_seconds=10.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.BURST,
    target_count=1,
)


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="runtime-delayed",
        plan=RotationPlan(
            character_name="Healer",
            build_name="Runtime Delayed Heal",
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
            delayed_seeds=(
                RotationHealerDelayedHealSeed(
                    time_seconds=2.0,
                    sequence=3,
                    source_name="Delayed Bloom",
                    coefficient_number=1,
                    modeled_heal=500.0,
                ),
            ),
            unresolved=(),
        )

    def resolve_component_magnitude(self, **kwargs):
        self.component_calls.append(kwargs)
        return RotationHealerComponentHealingResolution(
            modeled_heal=float(kwargs["context"].modeled_heal),
        )


class _DemandHealingService:
    def assess(self, **kwargs):
        delayed = kwargs["delayed_projection"]
        modeled = sum(event.modeled_heal for event in delayed.events)
        return RotationHealerDemandHealingEvidence(
            demand=kwargs["demand"],
            direct_events=(),
            periodic_events=(),
            delayed_events=delayed.events,
            modeled_direct_healing=0.0,
            modeled_periodic_healing=0.0,
            modeled_delayed_healing=modeled,
            unresolved=delayed.unresolved,
        )


def _provider(policy):
    action = _ActionHealingService()
    provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=action,
        delayed_runtime_evidence=(
            RotationHealerDelayedRuntimeEvidence(
                source_name="Delayed Bloom",
                coefficient_number=1,
                delay_seconds=4.0,
                provenance=("reviewed delayed magnitude fixture",),
                magnitude_policy=policy,
            ),
        ),
        demand_healing_service=_DemandHealingService(),
    )
    return provider, action


def test_recalculate_at_landing_uses_exact_runtime_context():
    provider, action = _provider(
        RotationHealerDelayedMagnitudePolicy.RECALCULATE_AT_LANDING
    )
    runtime_calls = []

    def runtime_context(time_seconds, sequence=None):
        runtime_calls.append((time_seconds, sequence))
        return SimpleNamespace(
            resolved=True,
            context=SimpleNamespace(modeled_heal=875.0),
            active_bar="front",
            unresolved=(),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert [(event.time_seconds, event.modeled_heal) for event in evidence.delayed_events] == [
        (6.0, 875.0)
    ]
    assert evidence.modeled_delayed_healing == pytest.approx(875.0)
    assert runtime_calls == [(6.0, 3)]
    assert [call["context"].modeled_heal for call in action.component_calls] == [875.0]
    assert evidence.unresolved == ()


def test_snapshot_at_cast_keeps_cast_resolved_delayed_magnitude():
    provider, action = _provider(
        RotationHealerDelayedMagnitudePolicy.SNAPSHOT_AT_CAST
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

    assert [event.modeled_heal for event in evidence.delayed_events] == [500.0]
    assert evidence.modeled_delayed_healing == pytest.approx(500.0)
    assert runtime_calls == []
    assert action.component_calls == []
    assert evidence.unresolved == ()


def test_recalculate_at_landing_fails_closed_when_context_is_unresolved():
    provider, action = _provider(
        RotationHealerDelayedMagnitudePolicy.RECALCULATE_AT_LANDING
    )

    def runtime_context(time_seconds, sequence=None):
        return SimpleNamespace(
            resolved=False,
            context=None,
            active_bar="front",
            unresolved=("landing-time proc state is unresolved",),
        )

    evidence = provider.evaluate_demand(
        candidate=_candidate(),
        demand=_DEMAND,
        runtime_build_context_resolver=runtime_context,
    )

    assert evidence.delayed_events == ()
    assert evidence.modeled_delayed_healing == pytest.approx(0.0)
    assert action.component_calls == []
    assert any("landing-time proc state is unresolved" in item for item in evidence.unresolved)
