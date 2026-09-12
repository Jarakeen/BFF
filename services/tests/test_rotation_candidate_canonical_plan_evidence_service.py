from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_effective_duration import RotationEffectiveDurationOverride
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _SustainService:
    def __init__(self, projection):
        self.projection = projection
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return self.projection


class _DurationService:
    def __init__(self, projection):
        self.projection = projection
        self.calls = []

    def analyze(self, plan, **kwargs):
        self.calls.append((plan, kwargs))
        return self.projection


class _WorkloadProvider:
    def __init__(self, workload):
        self.workload = workload
        self.calls = []

    def evaluate_plan(self, candidate):
        self.calls.append(candidate)
        return self.workload


class _RoleOutputProvider:
    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = []

    def evaluate_plan(self, candidate):
        self.calls.append(candidate)
        return self.evidence


def _sustain_projection(minimum_amount: int = 1000):
    return SimpleNamespace(
        run=SimpleNamespace(
            sustain=SimpleNamespace(
                minimum_amount=minimum_amount,
                ending_margin=minimum_amount,
                sustains=True,
            )
        )
    )


def test_provider_evaluates_exact_final_candidate_plan_through_shared_services() -> None:
    candidate = _candidate()
    build = object()
    sustain_projection = SimpleNamespace(
        run=SimpleNamespace(
            sustain=SimpleNamespace(
                minimum_amount=1375,
                ending_margin=9900,
                sustains=True,
            )
        )
    )
    duration_projection = object()
    sustain_service = _SustainService(sustain_projection)
    duration_service = _DurationService(duration_projection)
    restoration = object()
    maximum = object()
    context = object()
    recovery = object()
    override = RotationEffectiveDurationOverride(
        skill_name="combat_prayer",
        duration_seconds=12.0,
        source="test canonical duration evidence",
        bar="front",
    )

    service = RotationCandidateCanonicalPlanEvidenceService(
        build=build,
        sustain_service=sustain_service,
        duration_service=duration_service,
        resource=ResourceType.STAMINA,
        restoration_events=(restoration,),
        maximum_events=(maximum,),
        calculation_context=context,
        displayed_recovery_at=recovery,
        effective_duration_overrides=(override,),
    )

    evidence = service.evaluate_plan(candidate)

    assert sustain_service.calls == [
        {
            "build": build,
            "plan": candidate.plan,
            "resource": ResourceType.STAMINA,
            "restoration_events": (restoration,),
            "maximum_events": (maximum,),
            "calculation_context": context,
            "displayed_recovery_at": recovery,
        }
    ]
    assert duration_service.calls == [
        (
            candidate.plan,
            {"effective_duration_overrides": (override,)},
        )
    ]
    assert evidence.sustain is sustain_projection
    assert evidence.duration is duration_projection


def test_provider_uses_minimum_resource_as_sustain_headroom_not_ending_balance() -> None:
    candidate = _candidate()
    sustain_projection = SimpleNamespace(
        run=SimpleNamespace(
            sustain=SimpleNamespace(
                minimum_amount=250,
                ending_margin=12000,
                sustains=True,
            )
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(sustain_projection),
        duration_service=_DurationService(object()),
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.sustain_margin == 250.0


def test_provider_does_not_invent_role_or_support_measurements() -> None:
    candidate = _candidate()
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.role_output_value is None
    assert evidence.role_output_unresolved == ()
    assert evidence.assigned_support_value is None
    assert evidence.primary_role_displacement_seconds is None


def test_provider_carries_resolved_authoritative_role_output_for_exact_candidate() -> None:
    candidate = _candidate()
    output_provider = _RoleOutputProvider(
        RotationCandidateRoleOutputEvidence(
            candidate_id="candidate",
            value=143250.5,
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        role_output_evidence_provider=output_provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert output_provider.calls == [candidate]
    assert evidence.role_output_value == 143250.5
    assert evidence.role_output_unresolved == ()
    assert evidence.assigned_support_value is None


def test_provider_keeps_role_output_unknown_when_authority_reports_unresolved_evidence() -> None:
    candidate = _candidate()
    blocker = "light-attack damage consequence unresolved"
    output_provider = _RoleOutputProvider(
        RotationCandidateRoleOutputEvidence(
            candidate_id="candidate",
            value=143250.5,
            unresolved=(blocker,),
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        role_output_evidence_provider=output_provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.role_output_value is None
    assert evidence.role_output_unresolved == (blocker,)


def test_provider_rejects_role_output_evidence_for_a_different_candidate() -> None:
    candidate = _candidate()
    output_provider = _RoleOutputProvider(
        RotationCandidateRoleOutputEvidence(
            candidate_id="other-candidate",
            value=140000.0,
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        role_output_evidence_provider=output_provider,
    )

    with pytest.raises(ValueError, match="role-output evidence candidate mismatch"):
        service.evaluate_plan(candidate)


def test_role_output_evidence_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        RotationCandidateRoleOutputEvidence(
            candidate_id="candidate",
            value=float("nan"),
        )


def test_provider_uses_viable_canonical_workload_displacement_for_exact_candidate() -> None:
    candidate = _candidate()
    workload = SimpleNamespace(
        alternative_id="candidate",
        viable=True,
        primary_role_displacement_seconds=3.25,
        recipient_coverage_result=None,
        temporal_coverage_result=None,
    )
    workload_provider = _WorkloadProvider(workload)
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        provider_workload_evidence_provider=workload_provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert workload_provider.calls == [candidate]
    assert evidence.primary_role_displacement_seconds == 3.25
    assert evidence.assigned_support_value is None
    assert evidence.role_output_value is None


def test_provider_uses_canonical_temporal_coverage_ratio_as_assigned_support_value() -> None:
    candidate = _candidate()
    workload = SimpleNamespace(
        alternative_id="candidate",
        viable=True,
        primary_role_displacement_seconds=2.5,
        recipient_coverage_result=SimpleNamespace(fully_covered=True),
        temporal_coverage_result=SimpleNamespace(
            full_requirement_met=True,
            coverage_ratio=0.875,
        ),
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        provider_workload_evidence_provider=_WorkloadProvider(workload),
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.assigned_support_value == pytest.approx(0.875)
    assert evidence.primary_role_displacement_seconds == pytest.approx(2.5)


def test_provider_does_not_promote_boolean_only_workload_to_assigned_support() -> None:
    candidate = _candidate()
    workload = SimpleNamespace(
        alternative_id="candidate",
        viable=True,
        primary_role_displacement_seconds=1.0,
        recipient_coverage_result=None,
        temporal_coverage_result=None,
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        provider_workload_evidence_provider=_WorkloadProvider(workload),
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.assigned_support_value is None
    assert evidence.primary_role_displacement_seconds == pytest.approx(1.0)


def test_provider_keeps_displacement_and_support_unknown_when_workload_is_not_viable() -> None:
    candidate = _candidate()
    workload_provider = _WorkloadProvider(
        SimpleNamespace(
            alternative_id="candidate",
            viable=False,
            primary_role_displacement_seconds=0.0,
            recipient_coverage_result=SimpleNamespace(fully_covered=True),
            temporal_coverage_result=SimpleNamespace(
                full_requirement_met=True,
                coverage_ratio=1.0,
            ),
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        provider_workload_evidence_provider=workload_provider,
    )

    evidence = service.evaluate_plan(candidate)

    assert evidence.primary_role_displacement_seconds is None
    assert evidence.assigned_support_value is None


def test_provider_rejects_workload_evidence_for_a_different_candidate() -> None:
    candidate = _candidate()
    workload_provider = _WorkloadProvider(
        SimpleNamespace(
            alternative_id="different-candidate",
            viable=True,
            primary_role_displacement_seconds=1.0,
            recipient_coverage_result=None,
            temporal_coverage_result=None,
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(_sustain_projection()),
        duration_service=_DurationService(object()),
        provider_workload_evidence_provider=workload_provider,
    )

    with pytest.raises(ValueError, match="candidate mismatch"):
        service.evaluate_plan(candidate)
