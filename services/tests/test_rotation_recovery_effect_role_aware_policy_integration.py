from types import SimpleNamespace

from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeAssessment,
    RotationEffectUptimeRequirement,
    RotationEffectUptimeSummary,
)
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessment,
    RotationGameplayPolicyStatus,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RotationRecoveryHeavyFinalFamilyEvaluationService,
)
from services.rotation_role_aware_ranking_service import RotationRoleAwareRankingInput


_REQUIREMENT = RotationEffectUptimeRequirement(
    effect_name="major_brittle",
    source_skill_name="reviewed source",
    minimum_uptime=0.90,
    bar="back",
)


class _EffectUptimeService:
    def __init__(self, by_plan_name: dict[str, float]) -> None:
        self.by_plan_name = by_plan_name

    def assess(self, *, plan, build, requirements, passives=()):
        assert build is not None
        assert requirements == (_REQUIREMENT,)
        uptime = self.by_plan_name[plan.name]
        return (
            RotationEffectUptimeAssessment(
                requirement=_REQUIREMENT,
                summary=RotationEffectUptimeSummary(
                    effect_name=_REQUIREMENT.effect_name,
                    source_skill_name=_REQUIREMENT.source_skill_name,
                    bar=_REQUIREMENT.bar,
                    base_duration_seconds=4.0,
                    effective_duration_seconds=20.0,
                    cast_count=3,
                    active_seconds=60.0 * uptime,
                    uptime_fraction=uptime,
                    applied_modifier_sources=(),
                ),
            ),
        )


def _scorecard() -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=RotationPlanConsequence(
            resource_kind=RotationResourceConsequenceKind.NEUTRAL,
            cast_deltas=(),
            cost_deltas=(),
            total_cost_delta=0,
            minimum_resource_delta=0,
            ending_resource_delta=0,
            shortfall_delta=0,
            wait_delta=0,
        ),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _assessment(candidate_id: str, status: RotationGameplayPolicyStatus):
    return RotationGameplayPolicyAssessment(
        candidate_id=candidate_id,
        policy_id="dd_redundant_personal_heal",
        status=status,
        subject="personal_heal_skill_slot",
        confidence="strong_practice",
        reasons=(f"policy status: {status.value}",),
    )


def _input(
    candidate_id: str,
    *,
    damage: float,
    status: RotationGameplayPolicyStatus,
) -> RotationRoleAwareRankingInput:
    return RotationRoleAwareRankingInput(
        candidate_id=candidate_id,
        scorecard=_scorecard(),
        role_key="dd",
        role_output_value=damage,
        role_output_label="effective damage",
        assigned_support_value=0.0,
        assigned_support_label="assigned support coverage",
        sustain_margin=5000.0,
        primary_role_displacement_seconds=0.0,
        gameplay_policy_assessment=_assessment(candidate_id, status),
    )


def _snapshots(*candidate_ids: str):
    return tuple(
        SimpleNamespace(
            candidate_id=candidate_id,
            plan=SimpleNamespace(name=candidate_id),
        )
        for candidate_id in candidate_ids
    )


def test_effect_failure_cannot_be_rescued_by_clean_dd_policy_or_high_damage() -> None:
    snapshots = _snapshots("effect-fail-clean", "effect-pass-disfavored")
    inputs = {
        "effect-fail-clean": _input(
            "effect-fail-clean",
            damage=300_000.0,
            status=RotationGameplayPolicyStatus.SATISFIED,
        ),
        "effect-pass-disfavored": _input(
            "effect-pass-disfavored",
            damage=100_000.0,
            status=RotationGameplayPolicyStatus.DISFAVORED,
        ),
    }
    service = RotationRecoveryHeavyFinalFamilyEvaluationService(
        effect_uptime_service=_EffectUptimeService(
            {
                "effect-fail-clean": 0.80,
                "effect-pass-disfavored": 0.95,
            }
        )
    )

    ranked = service.evaluate_effects_role_aware(
        snapshots,
        build=object(),
        input_resolver=lambda snapshot: inputs[snapshot.candidate_id],
        requirements=(_REQUIREMENT,),
    )

    assert [item.candidate_id for item in ranked] == [
        "effect-pass-disfavored",
        "effect-fail-clean",
    ]
    assert ranked[0].tier.value == "eligible"
    assert ranked[1].tier.value == "ineligible"
    assert any("observed 80.00%, required 90.00%" in reason for reason in ranked[1].reasons)


def test_gameplay_policy_orders_dds_after_both_pass_required_effect_floor() -> None:
    snapshots = _snapshots("redundant-high", "clean-lower")
    inputs = {
        "redundant-high": _input(
            "redundant-high",
            damage=200_000.0,
            status=RotationGameplayPolicyStatus.DISFAVORED,
        ),
        "clean-lower": _input(
            "clean-lower",
            damage=100_000.0,
            status=RotationGameplayPolicyStatus.SATISFIED,
        ),
    }
    service = RotationRecoveryHeavyFinalFamilyEvaluationService(
        effect_uptime_service=_EffectUptimeService(
            {
                "redundant-high": 0.95,
                "clean-lower": 0.95,
            }
        )
    )

    ranked = service.evaluate_effects_role_aware(
        snapshots,
        build=object(),
        input_resolver=lambda snapshot: inputs[snapshot.candidate_id],
        requirements=(_REQUIREMENT,),
    )

    assert [item.candidate_id for item in ranked] == ["clean-lower", "redundant-high"]
    assert all(item.tier.value == "eligible" for item in ranked)
    assert "gameplay policy dd_redundant_personal_heal: satisfied" in ranked[0].reasons
    assert "gameplay policy dd_redundant_personal_heal: disfavored" in ranked[1].reasons
