from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_dd_whole_plan_damage_coverage_audit_service import (
    RotationDDWholePlanDamageCoverageAuditService,
)


class _Provider:
    def __init__(self, by_key):
        self.by_key = dict(by_key)
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        return self.by_key[(action.time_seconds, action.sequence)]


def _candidate(*actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="dd-coverage",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Coverage Audit",
            duration_seconds=12.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_audit_counts_resolved_and_groups_repeated_blockers() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    first_skill = RotationAction(
        0.0,
        1,
        RotationActionKind.SKILL,
        name="stampede",
        bar="front",
    )
    second_skill = RotationAction(
        6.0,
        0,
        RotationActionKind.SKILL,
        name="stampede",
        bar="front",
    )
    swap = RotationAction(7.0, 0, RotationActionKind.BAR_SWAP, bar="back")
    candidate = _candidate(light, first_skill, second_skill, swap)
    reason = "direct impact timing semantics unavailable"
    provider = _Provider(
        {
            (0.0, 0): RotationActionDamageEvidence(0.0, 0, 250.0),
            (0.0, 1): RotationActionDamageEvidence(
                0.0,
                1,
                None,
                unresolved=(reason,),
            ),
            (6.0, 0): RotationActionDamageEvidence(
                6.0,
                0,
                None,
                unresolved=(reason,),
            ),
        }
    )

    result = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    ).audit(candidate)

    assert result.candidate_id == "dd-coverage"
    assert result.total_damage_actions == 3
    assert result.resolved_damage_actions == 1
    assert result.unresolved_damage_actions == 2
    assert result.complete is False
    assert len(result.blockers) == 1
    blocker = result.blockers[0]
    assert blocker.action_kind is RotationActionKind.SKILL
    assert blocker.action_name == "stampede"
    assert blocker.reason == reason
    assert blocker.occurrence_count == 2
    assert blocker.occurrences == ((0.0, 1), (6.0, 0))
    assert [call[1] for call in provider.calls] == [light, first_skill, second_skill]


def test_audit_counts_missing_damage_value_as_explicit_blocker() -> None:
    heavy = RotationAction(4.0, 0, RotationActionKind.HEAVY_ATTACK, bar="back")
    candidate = _candidate(heavy)
    provider = _Provider(
        {(4.0, 0): RotationActionDamageEvidence(4.0, 0, None)}
    )

    result = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    ).audit(candidate)

    assert result.total_damage_actions == 1
    assert result.resolved_damage_actions == 0
    assert result.unresolved_damage_actions == 1
    assert result.blockers[0].action_kind is RotationActionKind.HEAVY_ATTACK
    assert result.blockers[0].action_name is None
    assert result.blockers[0].reason == "damage consequence unavailable"
    assert result.blockers[0].occurrences == ((4.0, 0),)


def test_audit_complete_when_all_damage_actions_resolve() -> None:
    skill = RotationAction(
        2.0,
        0,
        RotationActionKind.SKILL,
        name="spammable",
        bar="front",
    )
    candidate = _candidate(skill)
    provider = _Provider(
        {(2.0, 0): RotationActionDamageEvidence(2.0, 0, 1000.0)}
    )

    result = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    ).audit(candidate)

    assert result.complete is True
    assert result.total_damage_actions == 1
    assert result.resolved_damage_actions == 1
    assert result.unresolved_damage_actions == 0
    assert result.blockers == ()


def test_audit_rejects_evidence_for_different_action() -> None:
    skill = RotationAction(
        2.0,
        0,
        RotationActionKind.SKILL,
        name="spammable",
        bar="front",
    )
    candidate = _candidate(skill)
    provider = _Provider(
        {(2.0, 0): RotationActionDamageEvidence(3.0, 0, 1000.0)}
    )

    service = RotationDDWholePlanDamageCoverageAuditService(
        action_damage_evidence_provider=provider,
    )

    try:
        service.audit(candidate)
    except ValueError as exc:
        assert "damage evidence mismatch" in str(exc)
    else:
        raise AssertionError("expected mismatched action evidence to fail")
