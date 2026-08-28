import pytest

from minmax.character_progression import (
    MAX_ATTRIBUTE_POINTS,
    MAX_CHAMPION_POINTS,
    AttributeAllocation,
    ChampionPointState,
    CharacterProgression,
)


def test_attributes_are_a_single_fixed_pool():
    allocation = AttributeAllocation(health=20, magicka=22, stamina=22)

    assert allocation.total == MAX_ATTRIBUTE_POINTS
    assert allocation.is_complete


def test_attributes_can_be_incomplete_during_progression():
    allocation = AttributeAllocation(magicka=10)

    assert allocation.total == 10
    assert not allocation.is_complete


def test_attributes_cannot_exceed_64():
    with pytest.raises(ValueError):
        AttributeAllocation(health=21, magicka=22, stamina=22)


def test_champion_points_are_capped_at_3600():
    state = ChampionPointState(total=MAX_CHAMPION_POINTS)

    assert state.total == 3600

    with pytest.raises(ValueError):
        ChampionPointState(total=3601)


def test_each_cp_tree_allows_four_active_slots():
    state = ChampionPointState(total=1600, blue_slotted=4, red_slotted=4, green_slotted=4)

    assert (state.blue_slotted, state.red_slotted, state.green_slotted) == (4, 4, 4)


def test_cp_slot_limits_are_independent_of_cp_earning():
    with pytest.raises(ValueError):
        ChampionPointState(total=1600, blue_slotted=5)


def test_character_progression_defaults_to_level_50_with_empty_pools():
    progression = CharacterProgression()

    assert progression.level == 50
    assert progression.attributes.total == 0
    assert progression.champion_points.total == 0


def test_character_level_is_1_to_50():
    with pytest.raises(ValueError):
        CharacterProgression(level=0)

    with pytest.raises(ValueError):
        CharacterProgression(level=51)
