import pytest

from minmax.passive_math import (
    light_armor_critical_rating,
    light_armor_magicka_recovery_percent,
    light_armor_penetration,
    light_armor_spell_resistance,
    medium_armor_crit_damage_healing_percent,
    medium_armor_stamina_recovery_percent,
    medium_armor_weapon_spell_damage_percent,
    undaunted_mettle_resource_percent,
    warden_advanced_species_crit_damage,
    warden_flourish_recovery_percent,
    warden_frozen_armor_resistance,
)


def test_warden_flourish_is_twenty_percent_recovery():
    assert warden_flourish_recovery_percent() == 0.20


def test_warden_advanced_species_scales_per_slotted_animal_companion_skill():
    assert warden_advanced_species_crit_damage(0) == 0.0
    assert warden_advanced_species_crit_damage(1) == 0.05
    assert warden_advanced_species_crit_damage(3) == pytest.approx(0.15)


def test_warden_frozen_armor_scales_per_slotted_winters_embrace_skill():
    assert warden_frozen_armor_resistance(0) == 0.0
    assert warden_frozen_armor_resistance(1) == 1240.0
    assert warden_frozen_armor_resistance(2) == 2480.0


def test_undaunted_mettle_is_two_percent_per_equipped_armor_type_and_caps_at_three_types():
    assert undaunted_mettle_resource_percent(0) == 0.0
    assert undaunted_mettle_resource_percent(1) == 0.02
    assert undaunted_mettle_resource_percent(2) == 0.04
    assert undaunted_mettle_resource_percent(3) == 0.06
    assert undaunted_mettle_resource_percent(99) == 0.06


def test_light_armor_max_rank_values_scale_per_piece():
    assert light_armor_penetration(6) == 5634.0
    assert light_armor_magicka_recovery_percent(6) == 0.24
    assert light_armor_critical_rating(6) == 1314.0
    assert light_armor_spell_resistance(6) == 4356.0


def test_medium_armor_max_rank_values_scale_per_piece():
    assert medium_armor_weapon_spell_damage_percent(1) == 0.02
    assert medium_armor_crit_damage_healing_percent(1) == 0.02
    assert medium_armor_stamina_recovery_percent(1) == 0.04
