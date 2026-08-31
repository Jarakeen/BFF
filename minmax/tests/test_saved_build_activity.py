from minmax.saved_build_activity import create_saved_bar_activity_plan
from models.build_model import PlayerBuild


def test_saved_bar_activity_repeats_five_ordinary_front_bar_slots() -> None:
    build = PlayerBuild(
        FrontBarSkills=["Skill A", "Skill B", "Skill C", "Skill D", "Skill E", "Ultimate"],
    )

    plan = create_saved_bar_activity_plan(
        build,
        active_bar="front",
        duration_seconds=7.0,
    )

    assert [action.time_seconds for action in plan.actions] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    assert [action.skill_name for action in plan.actions] == [
        "Skill A", "Skill B", "Skill C", "Skill D", "Skill E", "Skill A", "Skill B"
    ]
    assert all(action.skill_name != "Ultimate" for action in plan.actions)


def test_saved_bar_activity_uses_back_bar_and_skips_empty_slots() -> None:
    build = PlayerBuild(
        BackBarSkills=["Skill A", "", "Skill C", "", "Skill E", "Ultimate"],
    )

    plan = create_saved_bar_activity_plan(
        build,
        active_bar="back",
        duration_seconds=4.0,
        first_action_seconds=0.5,
        action_interval_seconds=1.0,
    )

    assert [action.time_seconds for action in plan.actions] == [0.5, 1.5, 2.5, 3.5]
    assert [action.skill_name for action in plan.actions] == ["Skill A", "Skill C", "Skill E", "Skill A"]


def test_saved_bar_activity_rejects_invalid_timing_or_bar() -> None:
    build = PlayerBuild()

    for kwargs in (
        {"active_bar": "side"},
        {"duration_seconds": -1.0},
        {"first_action_seconds": -1.0},
        {"action_interval_seconds": 0.0},
    ):
        try:
            create_saved_bar_activity_plan(build, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid saved-bar plan inputs to be rejected: {kwargs}")
