from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessmentService,
    RotationGameplayPolicyContext,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_role_aware_ranking_service import (
    RotationRoleAwareRankingInput,
    RotationRoleAwareRankingService,
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


def _assessment(
    candidate_id: str,
    *,
    heal_slots: tuple[str, ...] = (),
    reliable_group_healing: bool | None = True,
    exception_contexts: tuple[str, ...] = (),
):
    return RotationGameplayPolicyAssessmentService().assess_dd_personal_heal(
        RotationGameplayPolicyContext(
            candidate_id=candidate_id,
            role="dd",
            content_type="trial",
            personal_heal_skill_slots=heal_slots,
            reliable_group_healing=reliable_group_healing,
            exception_contexts=exception_contexts,
        )
    )


def _candidate(
    candidate_id: str,
    *,
    output: float,
    assessment=None,
) -> RotationRoleAwareRankingInput:
    return RotationRoleAwareRankingInput(
        candidate_id=candidate_id,
        scorecard=_scorecard(),
        role_key="dd",
        role_output_value=output,
        role_output_label="effective damage",
        assigned_support_value=None,
        assigned_support_label="assigned support coverage",
        sustain_margin=1000.0,
        primary_role_displacement_seconds=0.0,
        gameplay_policy_assessment=assessment,
    )


def test_compliant_dd_beats_higher_damage_disfavored_personal_heal_candidate() -> None:
    compliant = _candidate(
        "compliant",
        output=120_000.0,
        assessment=_assessment("compliant"),
    )
    redundant_heal = _candidate(
        "redundant-heal",
        output=200_000.0,
        assessment=_assessment(
            "redundant-heal",
            heal_slots=("front:resolving_vigor",),
        ),
    )

    ranked = RotationRoleAwareRankingService().rank((redundant_heal, compliant))

    assert [item.candidate_id for item in ranked] == ["compliant", "redundant-heal"]
    assert all(item.tier.value == "eligible" for item in ranked)
    assert any("disfavored" in reason for reason in ranked[1].role_reasons)


def test_explicit_encounter_override_beats_disfavored_candidate_before_damage() -> None:
    justified = _candidate(
        "portal-heal",
        output=110_000.0,
        assessment=_assessment(
            "portal-heal",
            heal_slots=("back:resolving_vigor",),
            exception_contexts=("portal",),
        ),
    )
    redundant = _candidate(
        "redundant-heal",
        output=190_000.0,
        assessment=_assessment(
            "redundant-heal",
            heal_slots=("back:resolving_vigor",),
        ),
    )

    ranked = RotationRoleAwareRankingService().rank((redundant, justified))

    assert [item.candidate_id for item in ranked] == ["portal-heal", "redundant-heal"]
    assert any("overridden" in reason for reason in ranked[0].role_reasons)


def test_unresolved_dd_gameplay_policy_fails_closed() -> None:
    unresolved = _candidate(
        "unknown-coverage",
        output=220_000.0,
        assessment=_assessment(
            "unknown-coverage",
            heal_slots=("front:resolving_vigor",),
            reliable_group_healing=None,
        ),
    )
    resolved = _candidate(
        "resolved",
        output=100_000.0,
        assessment=_assessment("resolved"),
    )

    ranked = RotationRoleAwareRankingService().rank((unresolved, resolved))

    assert [item.candidate_id for item in ranked] == ["resolved", "unknown-coverage"]
    assert ranked[0].tier.value == "eligible"
    assert ranked[1].tier.value == "ineligible"
    assert any("unresolved" in reason for reason in ranked[1].role_reasons)


def test_legacy_dd_without_gameplay_assessment_keeps_damage_first_behavior() -> None:
    ranked = RotationRoleAwareRankingService().rank(
        (
            _candidate("lower", output=100_000.0),
            _candidate("higher", output=130_000.0),
        )
    )

    assert [item.candidate_id for item in ranked] == ["higher", "lower"]
    assert all(item.tier.value == "eligible" for item in ranked)


def test_gameplay_policy_candidate_identity_mismatch_is_rejected() -> None:
    assessment = _assessment("different-id")

    try:
        _candidate("candidate", output=100_000.0, assessment=assessment)
    except ValueError as exc:
        assert "candidate mismatch" in str(exc)
    else:
        raise AssertionError("expected gameplay-policy candidate mismatch to fail")
