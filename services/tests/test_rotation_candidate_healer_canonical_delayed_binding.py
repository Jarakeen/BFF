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
    RotationHealerDelayedHealSeed,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)


_DEMAND = RotationDemandWindow(
    name="bloom check",
    start_seconds=10.0,
    end_seconds=16.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.BURST,
    target_count=12,
)


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Tester",
            build_name="Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _ActionHealingService:
    def __init__(self, projection):
        self.projection = projection

    def project(self, **kwargs):
        return self.projection


class _EmptyPeriodicTimingService:
    def inspect(self, build):
        return SimpleNamespace(entries=(), unresolved=())


class _CanonicalDelayedTimingService:
    def __init__(self, *, runtime_evidence=None, unresolved=()):
        self.runtime_evidence = runtime_evidence
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            runtime_evidence=self.runtime_evidence,
            unresolved=self.unresolved,
        )


def _projection():
    return RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(),
        delayed_seeds=(
            RotationHealerDelayedHealSeed(
                time_seconds=6.0,
                sequence=1,
                source_name="Budding Seeds",
                coefficient_number=1,
                modeled_heal=900.0,
            ),
        ),
        unresolved=(),
    )


def _provider(*, canonical_delayed_timing_service, delayed_runtime_evidence=()):
    return RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=_ActionHealingService(_projection()),
        periodic_timing_service=_EmptyPeriodicTimingService(),
        canonical_delayed_timing_service=canonical_delayed_timing_service,
        delayed_runtime_evidence=tuple(delayed_runtime_evidence),
    )


def test_canonical_delayed_timing_is_bound_into_demand_evidence():
    canonical = _CanonicalDelayedTimingService(
        runtime_evidence=RotationHealerDelayedRuntimeEvidence(
            source_name="Budding Seeds",
            coefficient_number=1,
            delay_seconds=6.0,
            provenance=("coefficient-local wording: after 6 seconds",),
        )
    )

    evidence = _provider(
        canonical_delayed_timing_service=canonical,
    ).evaluate_demand(candidate=_candidate(), demand=_DEMAND)

    assert canonical.calls == [
        {"source_name": "Budding Seeds", "coefficient_number": 1}
    ]
    assert [event.time_seconds for event in evidence.delayed_events] == [12.0]
    assert evidence.modeled_delayed_healing == pytest.approx(900.0)
    assert evidence.unresolved == ()


def test_explicit_delayed_evidence_overrides_canonical_resolution():
    canonical = _CanonicalDelayedTimingService(
        unresolved=("canonical delayed timing should not be consulted",)
    )
    explicit = RotationHealerDelayedRuntimeEvidence(
        source_name="Budding Seeds",
        coefficient_number=1,
        delay_seconds=5.0,
        provenance=("reviewed override",),
    )

    evidence = _provider(
        canonical_delayed_timing_service=canonical,
        delayed_runtime_evidence=(explicit,),
    ).evaluate_demand(candidate=_candidate(), demand=_DEMAND)

    assert canonical.calls == []
    assert [event.time_seconds for event in evidence.delayed_events] == [11.0]
    assert evidence.unresolved == ()


def test_unresolved_canonical_delayed_timing_fails_closed():
    canonical = _CanonicalDelayedTimingService(
        runtime_evidence=None,
        unresolved=(
            "Budding Seeds coefficient 1: explicit delayed-heal offset is unresolved",
        ),
    )

    evidence = _provider(
        canonical_delayed_timing_service=canonical,
    ).evaluate_demand(candidate=_candidate(), demand=_DEMAND)

    assert evidence.delayed_events == ()
    assert evidence.modeled_delayed_healing == 0.0
    assert (
        "Budding Seeds coefficient 1: explicit delayed-heal offset is unresolved"
        in evidence.unresolved
    )
    assert any(
        "delayed healing runtime evidence unavailable" in item
        for item in evidence.unresolved
    )
