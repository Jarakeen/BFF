from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
    RotationCandidateRestorationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_heavy_attack_restoration_plan_evidence_service import (
    RotationCandidateHeavyAttackRestorationPlanEvidenceService,
)
from services.rotation_sustain_service import RotationSustainProjection


def _candidate(candidate_id: str = "candidate") -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _projection(*, unresolved=()) -> RotationSustainProjection:
    return RotationSustainProjection(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(
            sustain=SimpleNamespace(minimum_amount=1200, ending_margin=2400, sustains=True)
        ),
        series=((0.0, 1200.0),),
        unresolved=tuple(unresolved),
    )


class _SustainService:
    def __init__(self):
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return _projection(unresolved=("existing sustain note",))


class _DurationService:
    def analyze(self, plan, **kwargs):
        return object()


class _RestorationProvider:
    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = []

    def evaluate_plan(self, candidate):
        self.calls.append(candidate)
        return self.evidence


def test_candidate_restoration_events_are_merged_into_phase4_sustain_input() -> None:
    candidate = _candidate()
    static = ResourceRestorationEvent(
        time_seconds=2.0,
        resource=ResourceType.MAGICKA,
        amount=500.0,
        source="static test restore",
    )
    heavy = ResourceRestorationEvent(
        time_seconds=8.0,
        resource=ResourceType.MAGICKA,
        amount=3000.0,
        source="verified heavy restore",
    )
    provider = _RestorationProvider(
        RotationCandidateRestorationEvidence(
            candidate_id="candidate",
            restoration_events=(heavy,),
        )
    )
    sustain = _SustainService()
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=sustain,
        duration_service=_DurationService(),
        restoration_events=(static,),
        restoration_evidence_provider=provider,
    )

    result = service.evaluate_plan(candidate)

    assert provider.calls == [candidate]
    assert sustain.calls[0]["restoration_events"] == (static, heavy)
    assert result.sustain.unresolved == ("existing sustain note",)


def test_unresolved_candidate_restoration_is_carried_into_sustain_evidence() -> None:
    candidate = _candidate()
    provider = _RestorationProvider(
        RotationCandidateRestorationEvidence(
            candidate_id="candidate",
            unresolved=("fully charged heavy lacks verified base restore",),
        )
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        restoration_evidence_provider=provider,
    )

    result = service.evaluate_plan(candidate)

    assert result.sustain.unresolved == (
        "existing sustain note",
        "fully charged heavy lacks verified base restore",
    )


def test_candidate_restoration_rejects_evidence_for_another_candidate() -> None:
    provider = _RestorationProvider(
        RotationCandidateRestorationEvidence(candidate_id="other")
    )
    service = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=_SustainService(),
        duration_service=_DurationService(),
        restoration_evidence_provider=provider,
    )

    with pytest.raises(ValueError, match="restoration evidence candidate mismatch"):
        service.evaluate_plan(_candidate())


class _HeavyRestorationService:
    def __init__(self, projection):
        self.projection = projection
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return self.projection


def test_heavy_plan_provider_reuses_existing_projection_and_preserves_fail_closed_reasons() -> None:
    candidate = _candidate()
    event = ResourceRestorationEvent(
        time_seconds=4.0,
        resource=ResourceType.MAGICKA,
        amount=2500.0,
        source="verified heavy restore",
    )
    projection = SimpleNamespace(
        restoration_events=(event,),
        unresolved=("restore amount unresolved for second heavy",),
        weapon_projection=SimpleNamespace(
            violations=(SimpleNamespace(reason="heavy claims back bar while front is active"),)
        ),
    )
    delegate = _HeavyRestorationService(projection)
    canonical_build = object()
    completion = object()
    provider = RotationCandidateHeavyAttackRestorationPlanEvidenceService(
        build=canonical_build,
        initial_bar="front",
        completion_evidence=(completion,),
        restoration_service=delegate,
    )

    result = provider.evaluate_plan(candidate)

    assert delegate.calls == [
        {
            "build": canonical_build,
            "plan": candidate.plan,
            "initial_bar": "front",
            "completion_evidence": (completion,),
        }
    ]
    assert result.candidate_id == "candidate"
    assert result.restoration_events == (event,)
    assert result.unresolved == (
        "restore amount unresolved for second heavy",
        "heavy claims back bar while front is active",
    )


def test_heavy_plan_provider_resolves_completion_evidence_per_exact_candidate() -> None:
    projection = SimpleNamespace(
        restoration_events=(),
        unresolved=(),
        weapon_projection=SimpleNamespace(violations=()),
    )
    delegate = _HeavyRestorationService(projection)
    baseline_completion = object()
    heavy_completion = object()
    resolver_calls = []

    def resolve(candidate):
        resolver_calls.append(candidate.candidate_id)
        return {
            "baseline": (baseline_completion,),
            "heavy": (heavy_completion,),
        }[candidate.candidate_id]

    provider = RotationCandidateHeavyAttackRestorationPlanEvidenceService(
        build=object(),
        initial_bar="front",
        completion_evidence_resolver=resolve,
        restoration_service=delegate,
    )
    baseline = _candidate("baseline")
    heavy = _candidate("heavy")

    provider.evaluate_plan(baseline)
    provider.evaluate_plan(heavy)

    assert resolver_calls == ["baseline", "heavy"]
    assert delegate.calls[0]["completion_evidence"] == (baseline_completion,)
    assert delegate.calls[1]["completion_evidence"] == (heavy_completion,)
    assert delegate.calls[0]["plan"] is baseline.plan
    assert delegate.calls[1]["plan"] is heavy.plan


def test_heavy_plan_provider_rejects_ambiguous_fixed_and_resolved_completion_sources() -> None:
    with pytest.raises(ValueError, match="either a fixed tuple or a candidate resolver"):
        RotationCandidateHeavyAttackRestorationPlanEvidenceService(
            build=object(),
            initial_bar="front",
            completion_evidence=(object(),),
            completion_evidence_resolver=lambda candidate: (),
            restoration_service=_HeavyRestorationService(object()),
        )
