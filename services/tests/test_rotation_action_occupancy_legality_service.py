from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_action_occupancy_legality_service import (
    RotationActionOccupancyLegalityService,
    RotationActionOccupancyRule,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Occupancy Build",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _rule(
    kind: RotationActionKind,
    duration: float,
    *blocked: RotationActionKind,
    name: str | None = None,
    source: str = "verified timing evidence",
) -> RotationActionOccupancyRule:
    return RotationActionOccupancyRule(
        action_kind=kind,
        action_name=name,
        occupancy_seconds=duration,
        blocked_action_kinds=tuple(blocked),
        source=source,
    )


def test_explicit_heavy_window_blocks_skill_and_bar_swap() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(6.0, 0, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
        RotationAction(6.5, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(7.1, 0, RotationActionKind.SKILL, name="Budding Seeds", bar="back"),
    )
    assessment = RotationActionOccupancyLegalityService().assess(
        plan=plan,
        rules=(
            _rule(
                RotationActionKind.HEAVY_ATTACK,
                2.0,
                RotationActionKind.SKILL,
                RotationActionKind.BAR_SWAP,
            ),
        ),
    )

    assert assessment.is_legal is False
    assert len(assessment.violations) == 2
    assert {item.blocked_action.kind for item in assessment.violations} == {
        RotationActionKind.SKILL,
        RotationActionKind.BAR_SWAP,
    }
    assert all(item.window_end_seconds == 7.0 for item in assessment.violations)


def test_unblocked_light_attack_can_share_explicit_skill_window() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, name="Channel Skill", bar="front"),
        RotationAction(10.0, 1, RotationActionKind.LIGHT_ATTACK, bar="front"),
        RotationAction(11.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
    )
    assessment = RotationActionOccupancyLegalityService().assess(
        plan=plan,
        rules=(
            _rule(
                RotationActionKind.SKILL,
                1.5,
                RotationActionKind.BAR_SWAP,
                name="Channel Skill",
            ),
        ),
    )

    assert assessment.is_legal is False
    assert len(assessment.violations) == 1
    assert assessment.violations[0].blocked_action.kind is RotationActionKind.BAR_SWAP


def test_action_at_exact_window_end_is_legal() -> None:
    plan = _plan(
        RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(4.0, 0, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
    )
    assessment = RotationActionOccupancyLegalityService().assess(
        plan=plan,
        rules=(
            _rule(
                RotationActionKind.HEAVY_ATTACK,
                2.0,
                RotationActionKind.SKILL,
            ),
        ),
    )

    assert assessment.is_legal is True


def test_same_timestamp_sequence_is_respected() -> None:
    plan = _plan(
        RotationAction(8.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(8.0, 1, RotationActionKind.BAR_SWAP, bar="back"),
    )
    assessment = RotationActionOccupancyLegalityService().assess(
        plan=plan,
        rules=(
            _rule(
                RotationActionKind.HEAVY_ATTACK,
                2.0,
                RotationActionKind.BAR_SWAP,
            ),
        ),
    )

    assert assessment.is_legal is False
    assert assessment.violations[0].blocked_action.sequence == 1


def test_named_and_generic_rule_overlap_is_unresolved() -> None:
    plan = _plan(
        RotationAction(3.0, 0, RotationActionKind.SKILL, name="Radiating Regeneration", bar="front"),
    )
    assessment = RotationActionOccupancyLegalityService().assess(
        plan=plan,
        rules=(
            _rule(RotationActionKind.SKILL, 1.0, RotationActionKind.BAR_SWAP),
            _rule(
                RotationActionKind.SKILL,
                1.2,
                RotationActionKind.BAR_SWAP,
                name="Radiating Regeneration",
                source="skill-specific timing evidence",
            ),
        ),
    )

    assert assessment.is_legal is False
    assert assessment.violations == ()
    assert "multiple rotation occupancy rules match" in assessment.unresolved[0]


def test_missing_rule_does_not_invent_zero_or_blocking() -> None:
    plan = _plan(
        RotationAction(1.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        RotationAction(1.1, 0, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
    )

    assessment = RotationActionOccupancyLegalityService().assess(plan=plan, rules=())

    assert assessment.is_legal is True
    assert assessment.violations == ()
    assert assessment.unresolved == ()


def test_duplicate_semantic_rules_fail_closed() -> None:
    rule = _rule(
        RotationActionKind.SKILL,
        1.0,
        RotationActionKind.BAR_SWAP,
        name="Winter's Revenge",
    )
    duplicate = _rule(
        RotationActionKind.SKILL,
        1.0,
        RotationActionKind.BAR_SWAP,
        name="Winters Revenge",
    )

    try:
        RotationActionOccupancyLegalityService().assess(
            plan=_plan(),
            rules=(rule, duplicate),
        )
    except ValueError as exc:
        assert "duplicate rotation action occupancy rule" in str(exc)
    else:
        raise AssertionError("duplicate semantic occupancy rules must fail closed")
