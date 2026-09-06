from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_generation_sources import (
    CombatAttackUltimateGenerationSource,
    HeroismTier,
    HeroismUltimateGenerationSource,
    HeroismWindow,
)


def test_minor_heroism_generates_one_ultimate_every_one_point_five_seconds() -> None:
    events = HeroismUltimateGenerationSource().events(
        windows=(HeroismWindow(HeroismTier.MINOR, 0.0, 4.5, source="Minor Heroism"),),
        duration_seconds=4.5,
    )

    assert [(event.time_seconds, event.amount) for event in events] == [
        (1.5, 1.0),
        (3.0, 1.0),
        (4.5, 1.0),
    ]


def test_major_heroism_generates_three_ultimate_every_one_point_five_seconds() -> None:
    events = HeroismUltimateGenerationSource().events(
        windows=(HeroismWindow(HeroismTier.MAJOR, 2.0, 6.5, source="Major Heroism"),),
        duration_seconds=6.5,
    )

    assert [(event.time_seconds, event.amount) for event in events] == [
        (3.5, 3.0),
        (5.0, 3.0),
        (6.5, 3.0),
    ]


def test_heroism_generates_nothing_out_of_combat() -> None:
    events = HeroismUltimateGenerationSource().events(
        windows=(
            HeroismWindow(
                HeroismTier.MINOR,
                0.0,
                6.0,
                in_combat=False,
                source="Minor Heroism",
            ),
        ),
        duration_seconds=6.0,
    )

    assert events == ()


def test_multiple_heroism_windows_produce_ordered_events() -> None:
    events = HeroismUltimateGenerationSource().events(
        windows=(
            HeroismWindow(HeroismTier.MAJOR, 3.0, 4.5, source="Major Heroism"),
            HeroismWindow(HeroismTier.MINOR, 0.0, 3.0, source="Minor Heroism"),
        ),
        duration_seconds=4.5,
    )

    assert [(event.time_seconds, event.amount) for event in events] == [
        (1.5, 1.0),
        (3.0, 1.0),
        (4.5, 3.0),
    ]


def test_heroism_window_cannot_extend_beyond_generation_duration() -> None:
    try:
        HeroismUltimateGenerationSource().events(
            windows=(HeroismWindow(HeroismTier.MINOR, 0.0, 6.0),),
            duration_seconds=5.0,
        )
    except ValueError as exc:
        assert "cannot end after generation duration" in str(exc)
    else:
        raise AssertionError("Expected out-of-range Heroism window to fail")


def test_single_damaging_attack_generates_three_ultimate_per_second_for_nine_seconds() -> None:
    events = CombatAttackUltimateGenerationSource().events(
        attack_times=(0.0,),
        duration_seconds=12.0,
    )

    assert [(event.time_seconds, event.amount) for event in events] == [
        (float(second), 3.0) for second in range(1, 10)
    ]


def test_repeated_attacks_refresh_base_generation_without_stacking() -> None:
    events = CombatAttackUltimateGenerationSource().events(
        attack_times=(0.0, 5.0),
        duration_seconds=14.0,
    )

    assert [(event.time_seconds, event.amount) for event in events] == [
        (float(second), 3.0) for second in range(1, 15)
    ]


def test_base_generation_restarts_after_attack_buff_expires() -> None:
    events = CombatAttackUltimateGenerationSource().events(
        attack_times=(0.0, 20.0),
        duration_seconds=30.0,
    )

    assert [event.time_seconds for event in events] == [
        *[float(second) for second in range(1, 10)],
        *[float(second) for second in range(21, 30)],
    ]


def test_plan_attacks_require_explicit_success_assumption() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=3.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Skill", "front"),
            RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
        ),
    )
    source = CombatAttackUltimateGenerationSource()

    assert source.events_from_plan(
        plan=plan,
        assume_scheduled_attacks_damage=False,
    ) == ()

    events = source.events_from_plan(
        plan=plan,
        assume_scheduled_attacks_damage=True,
    )
    assert [(event.time_seconds, event.amount) for event in events] == [
        (1.0, 3.0),
        (2.0, 3.0),
        (3.0, 3.0),
    ]
