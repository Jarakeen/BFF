from minmax.build import Build
from minmax.build_gear import BuildGearSet


AKAVIRI_DRAGONGUARD_ID = 21
ARCHERS_MIND_ID = 23


def test_build_starts_with_no_gear_sets():
    build = Build()

    assert build.gear_sets == []


def test_build_can_add_gear_set():
    build = Build()

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    assert build.gear_sets == [
        BuildGearSet(
            set_id=AKAVIRI_DRAGONGUARD_ID,
            piece_count=4,
        )
    ]


def test_build_can_contain_multiple_gear_sets():
    build = Build()

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        5,
    )

    build.add_gear_set(
        ARCHERS_MIND_ID,
        5,
    )

    assert build.gear_sets == [
        BuildGearSet(
            set_id=AKAVIRI_DRAGONGUARD_ID,
            piece_count=5,
        ),
        BuildGearSet(
            set_id=ARCHERS_MIND_ID,
            piece_count=5,
        ),
    ]


def test_gear_set_is_immutable():
    gear_set = BuildGearSet(
        set_id=AKAVIRI_DRAGONGUARD_ID,
        piece_count=4,
    )

    try:
        gear_set.piece_count = 5
    except Exception:
        pass
    else:
        raise AssertionError("BuildGearSet should be immutable")