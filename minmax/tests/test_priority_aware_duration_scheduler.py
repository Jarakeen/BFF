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


def test_explicit_priority_orders_same_bar_no_duration_fillers() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=3.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Duration Skill", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Lower Filler", "front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, "Higher Filler", "front"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, "Duration Skill", "front"),
        ),
    )
    rules = (RotationRecastRule("Duration Skill", 10.0, bar="front"),)
    priorities = AbilityPriorityList(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        role="DD",
        entries=(
            AbilityPriorityEntry("front", 1, "Duration Skill", 2),
            AbilityPriorityEntry("front", 2, "Lower Filler", 20),
            AbilityPriorityEntry("front", 3, "Higher Filler", 1),
        ),
    )

    refined = PriorityAwareDurationRotationScheduler(priorities).refine(plan, rules)

    at_three = [
        action
        for action in refined.actions
        if action.time_seconds == 3.0 and action.kind is RotationActionKind.SKILL
    ]
    assert len(at_three) == 1
    assert at_three[0].name == "Higher Filler"


def test_displaced_and_incoming_same_bar_actions_are_ranked_by_explicit_priority() -> None:
    priorities = AbilityPriorityList(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        role="DD",
        entries=(
            AbilityPriorityEntry("back", 1, "Stampede", 1),
            AbilityPriorityEntry("back", 2, "Skeletal Archer", 3),
            AbilityPriorityEntry("back", 3, "Resolving Vigor", 4),
        ),
    )
    scheduler = PriorityAwareDurationRotationScheduler(priorities)
    queue = [
        RotationAction(18.0, 1, RotationActionKind.SKILL, "Stampede", "back"),
        RotationAction(19.0, 1, RotationActionKind.SKILL, "Resolving Vigor", "back"),
    ]
    incoming = RotationAction(
        20.0,
        1,
        RotationActionKind.SKILL,
        "Skeletal Archer",
        "back",
    )

    selected = scheduler._select_displaced_candidate(
        queue=queue,
        incoming=incoming,
        bar="back",
    )

    assert selected.name == "Stampede"
    assert [action.name for action in queue] == ["Skeletal Archer", "Resolving Vigor"]
