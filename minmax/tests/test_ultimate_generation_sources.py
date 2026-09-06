from minmax.ultimate_generation_sources import (
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
