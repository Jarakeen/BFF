from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessmentService,
    RotationGameplayPolicyContext,
    RotationGameplayPolicyStatus,
)


def _assess(**changes):
    values = dict(
        candidate_id="candidate",
        role="dd",
        content_type="trial",
        personal_heal_skill_slots=(),
        reliable_group_healing=True,
        exception_contexts=(),
    )
    values.update(changes)
    return RotationGameplayPolicyAssessmentService().assess_dd_personal_heal(
        RotationGameplayPolicyContext(**values)
    )


def test_dd_without_personal_heal_satisfies_policy() -> None:
    result = _assess()

    assert result.status is RotationGameplayPolicyStatus.SATISFIED
    assert result.disfavored is False
    assert result.resolved is True


def test_dd_personal_heal_with_reliable_group_healing_is_disfavored() -> None:
    result = _assess(personal_heal_skill_slots=("front:5 Resolving Vigor",))

    assert result.status is RotationGameplayPolicyStatus.DISFAVORED
    assert result.policy_id == "dd_redundant_personal_heal"
    assert result.personal_heal_skill_slots == ("front:5 Resolving Vigor",)
    assert any("normally does not spend" in reason for reason in result.reasons)


def test_dd_personal_heal_fails_closed_when_group_healing_reliability_is_unknown() -> None:
    result = _assess(
        personal_heal_skill_slots=("back:3 Resolving Vigor",),
        reliable_group_healing=None,
    )

    assert result.status is RotationGameplayPolicyStatus.UNRESOLVED
    assert result.resolved is False
    assert any("group-healing coverage is unresolved" in reason for reason in result.reasons)


def test_dd_personal_heal_is_allowed_when_group_healing_is_explicitly_unreliable() -> None:
    result = _assess(
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
        reliable_group_healing=False,
    )

    assert result.status is RotationGameplayPolicyStatus.OVERRIDDEN
    assert any("not redundant" in reason for reason in result.reasons)


def test_registered_encounter_exception_overrides_normal_dd_practice() -> None:
    result = _assess(
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
        exception_contexts=("portal_or_split_group_assignment",),
    )

    assert result.status is RotationGameplayPolicyStatus.OVERRIDDEN
    assert result.matched_exceptions == ("portal_or_split_group_assignment",)


def test_global_assignment_override_context_is_also_honored() -> None:
    result = _assess(
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
        exception_contexts=("portal",),
    )

    assert result.status is RotationGameplayPolicyStatus.OVERRIDDEN
    assert result.matched_exceptions == ("portal",)


def test_unknown_exception_context_does_not_silently_override_policy() -> None:
    result = _assess(
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
        exception_contexts=("because_i_felt_like_it",),
    )

    assert result.status is RotationGameplayPolicyStatus.DISFAVORED
    assert result.unknown_exception_contexts == ("because_i_felt_like_it",)
    assert any("does not establish an override" in reason for reason in result.reasons)


def test_non_dd_role_is_not_subject_to_dd_policy() -> None:
    result = _assess(
        role="healer",
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
    )

    assert result.status is RotationGameplayPolicyStatus.NOT_APPLICABLE


def test_non_organized_endgame_content_is_not_subject_to_dd_policy() -> None:
    result = _assess(
        content_type="dungeon",
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
    )

    assert result.status is RotationGameplayPolicyStatus.NOT_APPLICABLE


def test_dps_role_alias_normalizes_to_dd() -> None:
    result = _assess(
        role="DPS",
        personal_heal_skill_slots=("front:5 Resolving Vigor",),
    )

    assert result.status is RotationGameplayPolicyStatus.DISFAVORED
