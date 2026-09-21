from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_action_upper_bound_service import (
    ExtremeSustainedDPSActionUpperBoundService,
)
from services.extreme_sustained_dps_mundus_provisioning_dominance_service import (
    ExtremeSustainedDPSMundusProvisioningDominanceService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)


class _Evaluator:
    VALUES = {
        ("The Lover", "Food A"): 1000.0,
        ("The Lover", "Food B"): 1200.0,
        ("The Thief", "Food A"): 1500.0,
        ("The Thief", "Food B"): 1400.0,
    }

    def __init__(self, *, unresolved_pair=None):
        self.unresolved_pair = unresolved_pair

    def evaluate(self, build):
        pair = (build.Mundus, build.Food)
        if pair == self.unresolved_pair:
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=1.0,
                action_sequence=2,
                unresolved=("exact action damage unresolved",),
            )
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=1.0,
            action_sequence=2,
            occurrences=(
                RotationActionDamageOccurrence(
                    time_seconds=1.0,
                    sequence=2,
                    damage_value=self.VALUES[pair],
                    source_name="Skill",
                    coefficient_number=1,
                ),
            ),
        )


def _build():
    build = PlayerBuild()
    build.Mundus = "The Lover"
    build.Food = "Food A"
    return build


def _baseline_occurrences():
    return _Evaluator().evaluate(_build())


def test_joint_finite_search_proves_absolute_ceiling_for_both_axes() -> None:
    result = ExtremeSustainedDPSMundusProvisioningDominanceService.evaluate(
        candidate_key="candidate",
        baseline_build=_build(),
        mundus_choices=("The Thief", "The Lover"),
        food_choices=("Food B", "Food A"),
        evaluator=_Evaluator(),
    )

    assert result.expected_combinations == 4
    assert result.evaluated_combinations == 4
    assert result.resolved_combinations == 4
    assert result.winning_mundus == "The Thief"
    assert result.winning_food == "Food A"
    assert result.upper_bound_damage == 1500.0
    assert result.dominance.complete is True
    assert result.dominance.optimistic_upper_damage == 1500.0


def test_absolute_finite_ceiling_promotes_through_action_bound_bridge() -> None:
    finite = ExtremeSustainedDPSMundusProvisioningDominanceService.evaluate(
        candidate_key="candidate",
        baseline_build=_build(),
        mundus_choices=("The Lover", "The Thief"),
        food_choices=("Food A", "Food B"),
        evaluator=_Evaluator(),
    )
    promoted = ExtremeSustainedDPSActionUpperBoundService.from_occurrences(
        occurrence_evidence=_baseline_occurrences(),
        dominance=finite.dominance,
    )

    assert promoted.exact_damage == 1000.0
    assert promoted.bound.proven_safe is True
    assert promoted.bound.upper_bound_damage == 1500.0


def test_one_unresolved_joint_combination_withholds_dominance() -> None:
    result = ExtremeSustainedDPSMundusProvisioningDominanceService.evaluate(
        candidate_key="candidate",
        baseline_build=_build(),
        mundus_choices=("The Lover", "The Thief"),
        food_choices=("Food A", "Food B"),
        evaluator=_Evaluator(unresolved_pair=("The Thief", "Food B")),
    )

    assert result.expected_combinations == 4
    assert result.evaluated_combinations == 4
    assert result.resolved_combinations == 3
    assert result.upper_bound_damage is None
    assert result.dominance.complete is False
    assert any("The Thief + Food B" in item for item in result.unresolved)


def test_choices_are_deduplicated_without_shrinking_joint_denominator() -> None:
    result = ExtremeSustainedDPSMundusProvisioningDominanceService.evaluate(
        candidate_key="candidate",
        baseline_build=_build(),
        mundus_choices=("The Lover", "The Thief", "The Lover"),
        food_choices=("Food A", "Food B", "Food A"),
        evaluator=_Evaluator(),
    )

    assert result.expected_combinations == 4
    assert result.resolved_combinations == 4
