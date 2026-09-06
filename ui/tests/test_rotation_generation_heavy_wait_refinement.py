from types import SimpleNamespace

from models.build_model import PlayerBuild
from minmax.healer_wait_decision_provider import HealerHeavyAttackCandidate
from minmax.heavy_attack_opportunity import (
    HeavyAttackOpportunityEvidence,
    HeavyAttackPurpose,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Combat Prayer", "", "", "", "", "Eternal Guardian"]
    build.BackBarSkills = ["Overflowing Altar", "", "", "", "", "Aggressive Horn"]
    return build


def test_generation_routes_healer_heavy_candidates_into_duration_refinement() -> None:
    refinement_calls = []
    projection = SimpleNamespace(label="projection")
    evidence = SimpleNamespace(summary="duration evidence")

    class RefinementStub:
        def refine(self, plan, **kwargs):
            refinement_calls.append((plan, kwargs))
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class EvidenceStub:
        def from_projection(self, received):
            assert received is projection
            return evidence

    heavy = HealerHeavyAttackCandidate(
        "front",
        HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
            available_window_seconds=2.0,
            required_window_seconds=1.8,
            requirement_name="Roaring Opportunist",
        ),
    )

    support = RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
    )
    result = support.generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(
            duration_seconds=4.0,
            heavy_attack_candidates=(heavy,),
        ),
    )

    assert result.duration_evidence is evidence
    assert len(refinement_calls) == 1
    kwargs = refinement_calls[0][1]
    assert "wait_decision" in kwargs
    provider = kwargs["wait_decision"]
    assert provider is not None
    assert provider.candidates == (heavy,)
