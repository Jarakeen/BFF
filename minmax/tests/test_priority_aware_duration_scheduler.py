from minmax.priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


def test_explicit_priority_breaks_equal_due_refresh_tie() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=3.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Lower Priority", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Higher Priority", "front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, "Filler", "front"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, "Filler", "front"),
        ),
    )
    rules = (
        RotationRecastRule("Lower Priority", 3.0, bar="front"),
        RotationRecastRule("Higher Priority", 2.0, bar="front"),
    )
    priorities = AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Lower Priority", 10),
            AbilityPriorityEntry("front", 2, "Higher Priority", 1),
            AbilityPriorityEntry("front", 3, "Filler", 100),
        ),
    )

    refined = PriorityAwareDurationRotationScheduler(priorities).refine(plan, rules)

    at_three = [
        action
        for action in refined.actions
        if action.time_seconds == 3.0 and action.kind is RotationActionKind.SKILL
    ]
    assert len(at_three) == 1
    assert at_three[0].name == "Higher Priority"


def test_equal_priority_keeps_earlier_due_refresh_first() -> None:
    priorities = AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Earlier Due", 5),
            AbilityPriorityEntry("front", 2, "Later Due", 5),
        ),
    )
    scheduler = PriorityAwareDurationRotationScheduler(priorities)
    key = scheduler._due_refresh(
        time_seconds=5.0,
        bar="front",
        next_due={
            ("earlier due", "front"): 3.0,
            ("later due", "front"): 4.0,
        },
        rule_order={
            ("earlier due", "front"): 0,
            ("later due", "front"): 1,
        },
        action_kind_by_key={
            ("earlier due", "front"): RotationActionKind.SKILL,
            ("later due", "front"): RotationActionKind.SKILL,
        },
    )

    assert key == ("earlier due", "front")
