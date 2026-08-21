import pytest
from old_pages.old_damage_done import (
    calculate_aoe_damage_done,
    calculate_bleed_damage_done,
    calculate_bow_damage_done,
    calculate_damage_done,
    calculate_disease_damage_done,
    calculate_direct_damage_done,
    calculate_dot_damage_done,
    calculate_flame_damage_done,
    calculate_frost_damage_done,
    calculate_magic_damage_done,
    calculate_pet_damage_done,
    calculate_physical_damage_done,
    calculate_poison_damage_done,
    calculate_shock_damage_done,
    calculate_single_target_damage_done,
)


def test_calculate_dot_damage_done():
    assert calculate_dot_damage_done(
    cp_dot_damage_done=0.10,
    skill_dot_damage_done=0.05,
    set_dot_damage_done=0.08,
    ) == pytest.approx(0.23)


def test_calculate_dot_damage_done_all_zero_inputs():
    assert calculate_dot_damage_done() == 0.0


def test_calculate_direct_damage_done():
    assert calculate_direct_damage_done(
    cp_direct_damage_done=0.10,
    skill_direct_damage_done=0.05,
    set_direct_damage_done=0.08,
    ) == pytest.approx(0.23)

def test_calculate_single_target_damage_done():
    assert calculate_single_target_damage_done(
        skill_single_target_damage_done=0.12,
        cp_single_target_damage_done=0.08,
    ) == 0.20


def test_calculate_aoe_damage_done():
    assert calculate_aoe_damage_done(
    set_aoe_damage_done=0.10,
    skill_aoe_damage_done=0.05,
    cp_aoe_damage_done=0.08,
    ) == pytest.approx(0.23)


def test_calculate_magic_damage_done():
    assert calculate_magic_damage_done(
        cp_magic_damage_done=0.10,
        skill_magic_damage_done=0.05,
        buff_magic_damage_done=0.08,
        item_magic_damage_done=0.03,
        set_magic_damage_done=0.04,
    ) == 0.30


def test_calculate_physical_damage_done():
    assert calculate_physical_damage_done(
        cp_physical_damage_done=0.10,
        skill_physical_damage_done=0.05,
        buff_physical_damage_done=0.08,
        item_physical_damage_done=0.03,
        set_physical_damage_done=0.04,
    ) == 0.30


def test_calculate_shock_damage_done():
    assert calculate_shock_damage_done(
        cp_shock_damage_done=0.10,
        skill_shock_damage_done=0.05,
        buff_shock_damage_done=0.08,
        item_shock_damage_done=0.03,
        set_shock_damage_done=0.04,
    ) == 0.30


def test_calculate_flame_damage_done():
    assert calculate_flame_damage_done(
        cp_flame_damage_done=0.10,
        skill_flame_damage_done=0.05,
        buff_flame_damage_done=0.08,
        item_flame_damage_done=0.03,
        set_flame_damage_done=0.04,
    ) == 0.30


def test_calculate_frost_damage_done():
    assert calculate_frost_damage_done(
        cp_frost_damage_done=0.10,
        skill_frost_damage_done=0.05,
        buff_frost_damage_done=0.08,
        item_frost_damage_done=0.03,
        set_frost_damage_done=0.04,
    ) == 0.30


def test_calculate_poison_damage_done():
    assert calculate_poison_damage_done(
        cp_poison_damage_done=0.10,
        skill_poison_damage_done=0.05,
        buff_poison_damage_done=0.08,
        item_poison_damage_done=0.03,
        set_poison_damage_done=0.04,
    ) == 0.30


def test_calculate_disease_damage_done():
    assert calculate_disease_damage_done(
        cp_disease_damage_done=0.10,
        skill_disease_damage_done=0.05,
        buff_disease_damage_done=0.08,
        item_disease_damage_done=0.03,
        set_disease_damage_done=0.04,
    ) == 0.30


def test_calculate_bow_damage_done():
    assert calculate_bow_damage_done(
        cp_bow_damage_done=0.10,
        skill_bow_damage_done=0.05,
        buff_bow_damage_done=0.08,
        item_bow_damage_done=0.03,
        set_bow_damage_done=0.04,
    ) == 0.30


def test_calculate_bleed_damage_done():
    assert calculate_bleed_damage_done(
        set_bleed_damage_done=0.10,
        skill_bleed_damage_done=0.05,
    ) == pytest.approx(0.15)

def test_calculate_pet_damage_done():
    assert calculate_pet_damage_done(
    skill_pet_damage_done=0.10,
    set_pet_damage_done=0.05,
    ) == pytest.approx(0.15)


def test_calculate_damage_done():
    assert calculate_damage_done(
        cp_damage_done=0.10,
        skill_damage_done=0.05,
        buff_damage_done=0.08,
        item_damage_done=0.03,
        set_damage_done=0.04,
    ) == 0.30


def test_calculate_damage_done_all_zero_inputs():
    assert calculate_damage_done() == 0.0