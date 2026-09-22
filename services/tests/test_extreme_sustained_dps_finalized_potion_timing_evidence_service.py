from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from services.extreme_sustained_dps_finalized_potion_timing_evidence_service import (
    ExtremeSustainedDPSFinalizedPotionTimingEvidenceService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_resolver_composes_periodic_heavy_and_resource_timing_evidence(monkeypatch) -> None:
    import services.extreme_sustained_dps_finalized_potion_timing_evidence_service as module

    calls = []

    class _Timing:
        def __init__(self, database_path):
            calls.append(("timing", database_path))

    class _Projection:
        def __init__(self, timing, *, activation_anchor_resolver=None):
            calls.append(("projection-init", timing, activation_anchor_resolver))

        def project(self, *, plan, semantics):
            calls.append(("project", plan, semantics))
            return SimpleNamespace(unresolved=(), entries=("periodic-entry",))

    class _Registry:
        def load(self):
            calls.append(("registry",))
            return ("semantic-a",)

    class _Heavy:
        @staticmethod
        def completion_evidence_from_verified_reservations(plan):
            calls.append(("heavy", plan))
            return ("heavy-evidence",)

    monkeypatch.setattr(
        module,
        "RotationCandidatePeriodicDamageTimingEvidenceService",
        _Timing,
    )
    monkeypatch.setattr(
        module,
        "RotationCandidatePeriodicDamageRuntimeProjectionService",
        _Projection,
    )
    monkeypatch.setattr(
        module,
        "RotationHeavySustainProjectionService",
        _Heavy,
    )

    candidate = _candidate()
    anchor_resolver = object()
    service = ExtremeSustainedDPSFinalizedPotionTimingEvidenceService(
        database_path="fake.db",
        periodic_semantics_registry=_Registry(),
        activation_anchor_resolver_factory=lambda received: (
            anchor_resolver if received is candidate else None
        ),
        additional_resource_event_time_resolver=lambda received: (
            (3.0, 7.0) if received is candidate else ()
        ),
        additional_resource_event_denominator_proven=True,
    )

    result = service(candidate)

    assert result.periodic_projections[0].entries == ("periodic-entry",)
    assert result.heavy_attack_completion_evidence == ("heavy-evidence",)
    assert result.additional_resource_event_times == (3.0, 7.0)
    assert result.additional_resource_event_denominator_proven is True
    assert result.unresolved == ()
    assert ("registry",) in calls
    assert ("project", candidate.plan, ("semantic-a",)) in calls
    assert ("heavy", candidate.plan) in calls


def test_resolver_preserves_periodic_unresolved_evidence(monkeypatch) -> None:
    import services.extreme_sustained_dps_finalized_potion_timing_evidence_service as module

    class _Timing:
        def __init__(self, _database_path):
            pass

    class _Projection:
        def __init__(self, _timing, *, activation_anchor_resolver=None):
            pass

        def project(self, *, plan, semantics):
            return SimpleNamespace(
                unresolved=("periodic runtime gap",),
                entries=(),
            )

    class _Registry:
        def load(self):
            return ()

    class _Heavy:
        @staticmethod
        def completion_evidence_from_verified_reservations(_plan):
            return ()

    monkeypatch.setattr(
        module,
        "RotationCandidatePeriodicDamageTimingEvidenceService",
        _Timing,
    )
    monkeypatch.setattr(
        module,
        "RotationCandidatePeriodicDamageRuntimeProjectionService",
        _Projection,
    )
    monkeypatch.setattr(
        module,
        "RotationHeavySustainProjectionService",
        _Heavy,
    )

    result = ExtremeSustainedDPSFinalizedPotionTimingEvidenceService(
        database_path="fake.db",
        periodic_semantics_registry=_Registry(),
    )(_candidate())

    assert result.unresolved == ("periodic runtime gap",)
    assert result.additional_resource_event_denominator_proven is False
