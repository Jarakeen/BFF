from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSPotionTimingPolicy,
    ExtremeSustainedDPSRotationPolicyCandidate,
)
from services.extreme_sustained_dps_ultimate_added_action_count_proof_service import (
    ExtremeSustainedDPSUltimateAddedActionCountProofService,
)


def _candidate(*, option, availability=(), unresolved=(), projection_unresolved=()):
    projection = None
    if option != "none":
        projection = SimpleNamespace(
            unresolved=tuple(projection_unresolved),
            resource_projections=(
                (
                    option,
                    SimpleNamespace(availability_times=tuple(availability)),
                ),
            ),
            spend_rules=(SimpleNamespace(skill_name="Ultimate", cost=100.0),),
        )
    return ExtremeSustainedDPSRotationPolicyCandidate(
        structural_index=0,
        ultimate_option=option,
        potion_policy=ExtremeSustainedDPSPotionTimingPolicy(
            policy_id="potion:none",
            first_use_seconds=None,
        ),
        plan=SimpleNamespace(unresolved=()),
        ultimate_projection=projection,
        resource_legality=SimpleNamespace(is_legal=True, unresolved=()),
        evidence=(),
        unresolved=tuple(unresolved),
    )


def test_no_ultimate_policy_proves_zero_added_damage_actions() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(option="none")
    )

    assert result.maximum_additional_damage_actions == 0
    assert result.proof.complete is True


def test_resource_availability_count_proves_maximum_added_ultimate_actions() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(option="front", availability=(0.0, 12.0, 27.0))
    )

    assert result.maximum_additional_damage_actions == 3
    assert result.proof.complete is True


def test_competing_choice_diagnostic_does_not_break_explicit_policy_proof() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(
            option="back",
            availability=(5.0, 20.0),
            projection_unresolved=(
                "shared Ultimate projection selected back-bar 'A'; competing front-bar ultimate 'B' choice policy is unresolved",
            ),
        )
    )

    assert result.maximum_additional_damage_actions == 2
    assert result.proof.complete is True


def test_non_choice_projection_gap_forces_open() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(
            option="front",
            availability=(5.0,),
            projection_unresolved=("canonical Ultimate cost unresolved",),
        )
    )

    assert result.proof.complete is False
    assert "canonical Ultimate cost unresolved" in result.unresolved


def test_policy_level_unresolved_evidence_forces_open() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(
            option="front",
            availability=(5.0,),
            unresolved=("resource legality unresolved",),
        )
    )

    assert result.maximum_additional_damage_actions == 1
    assert result.proof.complete is False
