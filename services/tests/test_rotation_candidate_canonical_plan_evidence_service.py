from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_effective_duration import RotationEffectiveDurationOverride
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
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
    sustain_projection = SimpleNamespace(
        run=SimpleNamespace(
            sustain=SimpleNamespace(
                minimum_amount=1000,
                ending_margin=1000,
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

    assert evidence.role_output_value is None
    assert evidence.assigned_support_value is None
    assert evidence.primary_role_displacement_seconds is None
