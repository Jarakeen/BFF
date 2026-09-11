from types import SimpleNamespace

from minmax.skill_component_classification import (
    HealRecipientScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.rotation_candidate_gameplay_policy_context_service import (
    RotationCandidateGameplayPolicyContextService,
)
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessmentService,
    RotationGameplayPolicyStatus,
)


class _Coefficients:
    def __init__(self, by_name):
        self.by_name = by_name

    def resolve_name(self, name):
        value = self.by_name.get(name)
        if value is None:
            return SimpleNamespace(
                rank=None,
                unresolved=("skill identity unresolved",),
            )
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=value),
            unresolved=(),
        )


class _Components:
    def __init__(self, by_rank):
        self.by_rank = by_rank

    def get_for_skill_rank(self, rank_id):
        return self.by_rank.get(rank_id, ())


class _TooltipService:
    def __init__(self, by_name, by_rank):
        self.coefficients = _Coefficients(by_name)
        self.components = _Components(by_rank)


def _component(
    rank_id: int,
    *,
    kind: SkillEffectKind,
    scope: HealRecipientScope | None = None,
    number: int = 1,
):
    return SkillComponentClassification(
        skill_rank_id=rank_id,
        coefficient_number=number,
        effect_kind=kind,
        heal_recipient_scope=scope,
    )


def _service(
    *,
    front=(),
    back=(),
    by_name=None,
    by_rank=None,
    reliable_group_healing=True,
    exception_contexts=(),
):
    return RotationCandidateGameplayPolicyContextService(
        build=SimpleNamespace(FrontBarSkills=front, BackBarSkills=back),
        tooltip_service=_TooltipService(by_name or {}, by_rank or {}),
        role="dd",
        content_type="trial",
        reliable_group_healing=reliable_group_healing,
        exception_contexts=exception_contexts,
    )


def _candidate(candidate_id="candidate"):
    return SimpleNamespace(candidate_id=candidate_id)


def test_self_heal_component_marks_exact_saved_slot_as_personal_heal() -> None:
    service = _service(
        front=("Resolving Vigor",),
        by_name={"Resolving Vigor": 10},
        by_rank={
            10: (
                _component(
                    10,
                    kind=SkillEffectKind.HEAL,
                    scope=HealRecipientScope.SELF,
                ),
            )
        },
    )

    context = service.evaluate(_candidate("vigor"))

    assert context.candidate_id == "vigor"
    assert context.personal_heal_skill_slots == ("front:Resolving Vigor",)
    assert context.personal_heal_slot_evidence_resolved is True
    assert context.personal_heal_slot_unresolved == ()


def test_self_or_ally_heal_is_personal_but_group_only_heal_is_not() -> None:
    service = _service(
        front=("Flexible Heal", "Group Heal"),
        by_name={"Flexible Heal": 11, "Group Heal": 12},
        by_rank={
            11: (
                _component(
                    11,
                    kind=SkillEffectKind.HEAL,
                    scope=HealRecipientScope.SELF_OR_ALLY,
                ),
            ),
            12: (
                _component(
                    12,
                    kind=SkillEffectKind.HEAL,
                    scope=HealRecipientScope.GROUP,
                ),
            ),
        },
    )

    context = service.evaluate(_candidate())

    assert context.personal_heal_skill_slots == ("front:Flexible Heal",)
    assert context.personal_heal_slot_evidence_resolved is True


def test_unknown_skill_identity_fails_closed_instead_of_claiming_clean_bar() -> None:
    service = _service(front=("Mystery Skill",))

    context = service.evaluate(_candidate("unknown"))
    assessment = RotationGameplayPolicyAssessmentService().assess_dd_personal_heal(context)

    assert context.personal_heal_skill_slots == ()
    assert context.personal_heal_slot_evidence_resolved is False
    assert context.personal_heal_slot_unresolved == (
        "front:Mystery Skill: skill identity unresolved",
    )
    assert assessment.status is RotationGameplayPolicyStatus.UNRESOLVED
    assert "personal-heal slot classification is unresolved" in assessment.reasons


def test_heal_with_unknown_recipient_scope_fails_closed() -> None:
    service = _service(
        back=("Unreviewed Heal",),
        by_name={"Unreviewed Heal": 13},
        by_rank={
            13: (
                _component(
                    13,
                    kind=SkillEffectKind.HEAL,
                    scope=None,
                ),
            )
        },
    )

    context = service.evaluate(_candidate())

    assert context.personal_heal_slot_evidence_resolved is False
    assert context.personal_heal_slot_unresolved == (
        "back:Unreviewed Heal: personal-heal recipient classification unresolved",
    )


def test_known_nonheal_and_group_heal_prove_no_personal_heal_slot() -> None:
    service = _service(
        front=("Damage Skill",),
        back=("Group Heal",),
        by_name={"Damage Skill": 14, "Group Heal": 15},
        by_rank={
            14: (_component(14, kind=SkillEffectKind.DAMAGE),),
            15: (
                _component(
                    15,
                    kind=SkillEffectKind.HEAL,
                    scope=HealRecipientScope.GROUP,
                ),
            ),
        },
    )

    context = service.evaluate(_candidate("clean"))
    assessment = RotationGameplayPolicyAssessmentService().assess_dd_personal_heal(context)

    assert context.personal_heal_skill_slots == ()
    assert context.personal_heal_slot_evidence_resolved is True
    assert assessment.status is RotationGameplayPolicyStatus.SATISFIED


def test_explicit_encounter_exception_survives_canonical_slot_projection() -> None:
    service = _service(
        front=("Personal Heal",),
        by_name={"Personal Heal": 16},
        by_rank={
            16: (
                _component(
                    16,
                    kind=SkillEffectKind.HEAL,
                    scope=HealRecipientScope.SELF,
                ),
            )
        },
        exception_contexts=("portal",),
    )

    context = service.evaluate(_candidate("portal-dd"))
    assessment = RotationGameplayPolicyAssessmentService().assess_dd_personal_heal(context)

    assert context.exception_contexts == ("portal",)
    assert assessment.status is RotationGameplayPolicyStatus.OVERRIDDEN


def test_saved_slot_classification_is_cached_across_candidate_family() -> None:
    tooltip = _TooltipService(
        {"Personal Heal": 17},
        {
            17: (
                _component(
                    17,
                    kind=SkillEffectKind.HEAL,
                    scope=HealRecipientScope.SELF,
                ),
            )
        },
    )
    calls = {"count": 0}
    original = tooltip.coefficients.resolve_name

    def counted(name):
        calls["count"] += 1
        return original(name)

    tooltip.coefficients.resolve_name = counted
    service = RotationCandidateGameplayPolicyContextService(
        build=SimpleNamespace(
            FrontBarSkills=("Personal Heal",),
            BackBarSkills=(),
        ),
        tooltip_service=tooltip,
        role="dd",
        content_type="trial",
        reliable_group_healing=True,
    )

    first = service.evaluate(_candidate("a"))
    second = service.evaluate(_candidate("b"))

    assert first.personal_heal_skill_slots == second.personal_heal_skill_slots
    assert calls["count"] == 1
