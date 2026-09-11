from types import SimpleNamespace

from minmax.skill_component_classification import HealTemporalScope
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerComponentHealingResolution,
)


class _ActionHealingService:
    def __init__(self):
        self.calls = []

    def resolve_component_magnitude(self, **kwargs):
        self.calls.append(kwargs)
        return RotationHealerComponentHealingResolution(modeled_heal=500.0)


class _UnusedPeriodicTiming:
    def inspect(self, build):
        return SimpleNamespace(entries=(), unresolved=())


class _UnusedPeriodicEvidence:
    pass


class _UnusedDemandHealing:
    pass


def _provider(action):
    return RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path="unused.sqlite",
        build=object(),
        context=object(),
        action_healing_service=action,
        periodic_timing_service=_UnusedPeriodicTiming(),
        periodic_runtime_evidence_service=_UnusedPeriodicEvidence(),
        demand_healing_service=_UnusedDemandHealing(),
    )


def _runtime_context(time_seconds, sequence=None):
    return SimpleNamespace(
        resolved=True,
        context=object(),
        active_bar="front",
        unresolved=(),
    )


def _seed():
    return SimpleNamespace(source_name="Heal", coefficient_number=2)


def test_periodic_runtime_magnitude_requests_periodic_component_scope():
    action = _ActionHealingService()
    resolver = _provider(action)._runtime_periodic_magnitude_resolver(_runtime_context)

    result = resolver(_seed(), 5.0, 3)

    assert result.resolved is True
    assert action.calls[0]["expected_temporal_scope"] is HealTemporalScope.PERIODIC


def test_delayed_runtime_magnitude_requests_delayed_component_scope():
    action = _ActionHealingService()
    resolver = _provider(action)._runtime_delayed_magnitude_resolver(_runtime_context)

    result = resolver(_seed(), 7.0, 4)

    assert result.resolved is True
    assert action.calls[0]["expected_temporal_scope"] is HealTemporalScope.DELAYED
