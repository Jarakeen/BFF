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
    RotationCandidateHealerRoleOutputService,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerDelayedHealSeed,
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeEvidence,
)


_DEMAND = RotationDemandWindow(
    name="healing check",
    start_seconds=10.0,
    end_seconds=15.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=12,
)


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="healer-candidate",
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Demand Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _ActionHealingService:
    def __init__(self, projection):
        self.projection = projection
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return self.projection


class _PeriodicTimingService:
    def __init__(self, entries=(), unresolved=()):
        self.entries = tuple(entries)
        self.unresolved = tuple(unresolved)

    def inspect(self, build):
        return SimpleNamespace(entries=self.entries, unresolved=self.unresolved)


class _PeriodicRuntimeEvidenceService:
    def __init__(self, runtime_evidence=None, unresolved=()):
        self.runtime_evidence = runtime_evidence
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            runtime_evidence=self.runtime_evidence,
            unresolved=self.unresolved,
        )


def _provider(
    projection,
    *,
    periodic_timing_service=None,
    periodic_runtime_evidence_service=None,
    delayed_runtime_evidence=(),
    contexts_by_bar=None,
    action_healing_service=None,
):
    return RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        contexts_by_bar=contexts_by_bar,
        action_healing_service=(
            action_healing_service or _ActionHealingService(projection)
        ),
        periodic_timing_service=periodic_timing_service or _PeriodicTimingService(),
        periodic_runtime_evidence_service=(
            periodic_runtime_evidence_service or _PeriodicRuntimeEvidenceService()
        ),
        delayed_runtime_evidence=tuple(delayed_runtime_evidence),
    )


def test_direct_healing_flows_from_candidate_projection_into_role_output() -> None:
    projection = RotationHealerActionHealingProjection(
        direct_events=(
            RotationHealerResolvedHealEvent(
                time_seconds=12.0,
                sequence=1,
                source_name="Burst Heal",
                coefficient_number=1,
                modeled_heal=1000.0,
            ),
        ),
        periodic_seeds=(),
        delayed_seeds=(),
        unresolved=(),
    )
    role_output = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=_provider(projection),
    ).evaluate_plan(_candidate())

    # target_count=12 is deliberately not a multiplier; modeled healer evidence
    # remains pre-recipient and pre-overheal.
    assert role_output.resolved_value == pytest.approx(200.0)
    assert role_output.unresolved == ()


def test_periodic_healing_uses_bound_runtime_ticks_inside_exact_demand_window() -> None:
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(
            RotationHealerPeriodicHealSeed(
                time_seconds=8.0,
                sequence=1,
                source_name="Illustrious Healing",
                coefficient_number=2,
                modeled_heal=250.0,
            ),
        ),
        delayed_seeds=(),
        unresolved=(),
    )
    timing = _PeriodicTimingService(
        entries=(
            SimpleNamespace(
                skill_name="Illustrious Healing",
                coefficient_number=2,
                timing="canonical-periodic-timing",
            ),
        )
    )
    runtime_binding = _PeriodicRuntimeEvidenceService(
        runtime_evidence=RotationHealerPeriodicRuntimeEvidence(
            source_name="Illustrious Healing",
            coefficient_number=2,
            duration_seconds=10.0,
            tick_interval_seconds=2.0,
            first_tick_offset_seconds=2.0,
            tick_on_expiry_boundary=True,
        )
    )

    evidence = _provider(
        projection,
        periodic_timing_service=timing,
        periodic_runtime_evidence_service=runtime_binding,
    ).evaluate_demand(candidate=_candidate(), demand=_DEMAND)

    assert [event.time_seconds for event in evidence.periodic_events] == [10.0, 12.0, 14.0]
    assert evidence.modeled_periodic_healing == pytest.approx(750.0)
    assert evidence.modeled_total_healing == pytest.approx(750.0)
    assert evidence.unresolved == ()
    assert runtime_binding.calls[0]["canonical"] == "canonical-periodic-timing"
    assert runtime_binding.calls[0]["repeated_applications"] is False


def test_delayed_healing_uses_explicit_delay_evidence_before_demand_filtering() -> None:
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(),
        delayed_seeds=(
            RotationHealerDelayedHealSeed(
                time_seconds=9.0,
                sequence=1,
                source_name="Delayed Bloom",
                coefficient_number=1,
                modeled_heal=500.0,
            ),
        ),
        unresolved=(),
    )
    provider = _provider(
        projection,
        delayed_runtime_evidence=(
            RotationHealerDelayedRuntimeEvidence(
                source_name="Delayed Bloom",
                coefficient_number=1,
                delay_seconds=2.0,
                provenance=("reviewed coefficient-local wording",),
            ),
        ),
    )

    evidence = provider.evaluate_demand(candidate=_candidate(), demand=_DEMAND)

    assert [event.time_seconds for event in evidence.delayed_events] == [11.0]
    assert evidence.modeled_delayed_healing == pytest.approx(500.0)
    assert evidence.unresolved == ()


def test_missing_periodic_runtime_facts_fail_closed_in_role_output() -> None:
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(
            RotationHealerPeriodicHealSeed(
                time_seconds=8.0,
                sequence=1,
                source_name="Illustrious Healing",
                coefficient_number=2,
                modeled_heal=250.0,
            ),
        ),
        delayed_seeds=(),
        unresolved=(),
    )
    timing = _PeriodicTimingService(
        entries=(
            SimpleNamespace(
                skill_name="Illustrious Healing",
                coefficient_number=2,
                timing="canonical-periodic-timing",
            ),
        )
    )
    runtime_binding = _PeriodicRuntimeEvidenceService(
        runtime_evidence=None,
        unresolved=(
            "Illustrious Healing coefficient 2: first-tick offset is not verified",
        ),
    )
    role_output = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=_provider(
            projection,
            periodic_timing_service=timing,
            periodic_runtime_evidence_service=runtime_binding,
        ),
    ).evaluate_plan(_candidate())

    assert role_output.value is None
    assert role_output.resolved_value is None
    assert "Illustrious Healing coefficient 2: first-tick offset is not verified" in role_output.unresolved
    assert any("periodic healing runtime evidence unavailable" in item for item in role_output.unresolved)


def test_bar_context_map_is_forwarded_to_action_healing_projection() -> None:
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(),
        delayed_seeds=(),
        unresolved=(),
    )
    action_service = _ActionHealingService(projection)
    front_context = object()
    back_context = object()
    provider = _provider(
        projection,
        action_healing_service=action_service,
        contexts_by_bar={"front": front_context, "back": back_context},
    )

    provider.evaluate_demand(candidate=_candidate(), demand=_DEMAND)

    assert action_service.calls[0]["contexts_by_bar"] == {
        "front": front_context,
        "back": back_context,
    }
