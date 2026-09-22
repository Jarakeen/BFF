from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSPotionTimingPolicy,
    ExtremeSustainedDPSRotationPolicyCandidate,
)
from services.extreme_sustained_dps_ultimate_added_action_count_proof_service import (
    ExtremeSustainedDPSUltimateAddedActionCountProofService,
)


def _candidate(*, option, cast_times=(), unresolved=(), legal=True, legality_unresolved=()):
    actions = tuple(
        RotationAction(
            float(time_seconds),
            index,
            RotationActionKind.ULTIMATE,
            "Ultimate",
            option if option in {"front", "back"} else "front",
        )
        for index, time_seconds in enumerate(cast_times)
    )
    plan = RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=max(tuple(cast_times) + (0.0,)),
        actions=actions,
    )
    return ExtremeSustainedDPSRotationPolicyCandidate(
        structural_index=0,
        ultimate_option=option,
        potion_policy=ExtremeSustainedDPSPotionTimingPolicy(
            policy_id="potion:none",
            first_use_seconds=None,
        ),
        plan=plan,
        ultimate_projection=None,
        resource_legality=SimpleNamespace(
            is_legal=legal,
            unresolved=tuple(legality_unresolved),
        ),
        evidence=(),
        unresolved=tuple(unresolved),
    )


def test_no_ultimate_policy_proves_zero_added_damage_actions() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(option="none")
    )

    assert result.maximum_additional_damage_actions == 0
    assert result.proof.complete is True


def test_scheduled_ultimate_count_proves_maximum_added_ultimate_actions() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(option="front", cast_times=(0.0, 12.0, 27.0))
    )

    assert result.maximum_additional_damage_actions == 3
    assert result.proof.complete is True


def test_illegal_scheduled_policy_forces_open() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(
            option="front",
            cast_times=(5.0,),
            legal=False,
            legality_unresolved=("canonical Ultimate cost unresolved",),
        )
    )

    assert result.maximum_additional_damage_actions == 1
    assert result.proof.complete is False
    assert "canonical Ultimate cost unresolved" in result.unresolved


def test_policy_level_unresolved_evidence_forces_open() -> None:
    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(
        _candidate(
            option="front",
            cast_times=(5.0,),
            unresolved=("resource legality unresolved",),
        )
    )

    assert result.maximum_additional_damage_actions == 1
    assert result.proof.complete is False



def test_only_selected_bar_ultimate_actions_are_counted() -> None:
    plan = RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=2.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.ULTIMATE, "Front Ultimate", "front"),
            RotationAction(2.0, 0, RotationActionKind.ULTIMATE, "Back Ultimate", "back"),
        ),
    )
    policy = ExtremeSustainedDPSRotationPolicyCandidate(
        structural_index=0,
        ultimate_option="front",
        potion_policy=ExtremeSustainedDPSPotionTimingPolicy(
            policy_id="potion:none",
            first_use_seconds=None,
        ),
        plan=plan,
        ultimate_projection=None,
        resource_legality=SimpleNamespace(is_legal=True, unresolved=()),
        evidence=(),
        unresolved=(),
    )

    result = ExtremeSustainedDPSUltimateAddedActionCountProofService.prove(policy)

    assert result.maximum_additional_damage_actions == 1
    assert result.proof.complete is True
