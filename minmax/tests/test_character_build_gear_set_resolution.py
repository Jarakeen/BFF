import sqlite3

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.gear_piece import (
    ArmorPiece,
    GearPieceCategory,
    GearSlot,
)
from minmax.character_build.support_effect_resolver import (
    CharacterBuildSupportEffectResolver,
    equipped_gear_set_counts,
)
from minmax.character_build.bar import Bar
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.character_build.character_class import CharacterClass
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.role import Role


MASTER_ARCHITECT_ID = 332
MASTER_ARCHITECT_BONUS_ID = 1493


def _make_db(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );

            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );

            INSERT INTO gear_set
                VALUES (332, 'Master Architect', 'standard', 5);

            INSERT INTO gear_set_bonus VALUES
                (1490, 332, 2, '(2 items) Adds 25-1096 Maximum Magicka'),
                (1491, 332, 3, '(3 items) Gain Minor Slayer'),
                (1492, 332, 4, '(4 items) Adds 3-129 Weapon and Spell Damage'),
                (1493, 332, 5, '(5 items) Major Slayer');
            """
        )


def _piece(slot, set_id="332"):
    return ArmorPiece(
        slot=slot,
        category=GearPieceCategory.SET_PIECE,
        set_id=set_id,
    )


def _build(*pieces):
    slots = tuple(
        SlottedSkill(
            skill_id=f"test_skill_{i}",
            skill_line_id="animal_companions",
            is_ultimate=(i == 5),
        )
        for i in range(6)
    )

    front_bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=slots,
    )

    return CharacterBuild(
        name="Test Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=tuple(pieces),
        front_bar=front_bar,
    )


def test_counts_equipped_set_pieces():
    build = _build(
        _piece(GearSlot.HEAD),
        _piece(GearSlot.CHEST),
        _piece(GearSlot.LEGS),
        _piece(GearSlot.FEET),
        _piece(GearSlot.HANDS),
    )

    assert equipped_gear_set_counts(build) == {"332": 5}


def test_four_master_architect_pieces_do_not_grant_five_piece_bonus(tmp_path):
    db_path = tmp_path / "test.db"
    _make_db(db_path)

    build = _build(
        _piece(GearSlot.HEAD),
        _piece(GearSlot.CHEST),
        _piece(GearSlot.LEGS),
        _piece(GearSlot.FEET),
    )

    resolver = CharacterBuildSupportEffectResolver(
        gear_set_effect_variant_resolver=GearSetEffectVariantResolver(
            GearSetRepository(db_path)
        )
    )

    registry = resolver.resolve(build, active_bar=BarId.FRONT)
    
    assert not any(effect.name == "major_slayer" for effect in registry.all())


def test_five_master_architect_pieces_grant_major_slayer(tmp_path):
    db_path = tmp_path / "test.db"
    _make_db(db_path)

    build = _build(
        _piece(GearSlot.HEAD),
        _piece(GearSlot.CHEST),
        _piece(GearSlot.LEGS),
        _piece(GearSlot.FEET),
        _piece(GearSlot.HANDS),
    )

    resolver = CharacterBuildSupportEffectResolver(
        gear_set_effect_variant_resolver=GearSetEffectVariantResolver(
            GearSetRepository(db_path)
        )
    )

    registry = resolver.resolve(build, active_bar=BarId.FRONT)

    major_slayer = [
        effect for effect in registry.all()
        if effect.name == "major_slayer"
    ]

    assert len(major_slayer) == 1
    
    
def test_counts_set_pieces_on_both_weapon_bars():
    front_weapon = Weapon(
        weapon_type=WeaponType.RESTORATION_STAFF,
        set_id="332",
    )

    back_weapon = Weapon(
        weapon_type=WeaponType.FROST_STAFF,
        set_id="332",
    )

    slots = tuple(
        SlottedSkill(
            skill_id=f"test_skill_{i}",
            skill_line_id="animal_companions",
            is_ultimate=(i == 5),
        )
        for i in range(6)
    )

    build = CharacterBuild(
        name="Test Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(
            _piece(GearSlot.HEAD),
            _piece(GearSlot.CHEST),
            _piece(GearSlot.LEGS),
        ),
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=front_weapon,
            off_hand=None,
            slots=slots,
        ),
        back_bar=Bar(
            bar_id=BarId.BACK,
            main_hand=back_weapon,
            off_hand=None,
            slots=slots,
        ),
    )

    assert equipped_gear_set_counts(build) == {"332": 5}    
    
    
def test_split_armor_and_weapon_set_resolves_major_slayer(tmp_path):
    db_path = tmp_path / "test.db"
    _make_db(db_path)

    slots = tuple(
        SlottedSkill(
            skill_id=f"test_skill_{i}",
            skill_line_id="animal_companions",
            is_ultimate=(i == 5),
        )
        for i in range(6)
    )

    build = CharacterBuild(
        name="Test Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(
            _piece(GearSlot.HEAD),
            _piece(GearSlot.CHEST),
            _piece(GearSlot.LEGS),
        ),
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(
                weapon_type=WeaponType.RESTORATION_STAFF,
                set_id="332",
            ),
            off_hand=None,
            slots=slots,
        ),
        back_bar=Bar(
            bar_id=BarId.BACK,
            main_hand=Weapon(
                weapon_type=WeaponType.FROST_STAFF,
                set_id="332",
            ),
            off_hand=None,
            slots=slots,
        ),
    )

    resolver = CharacterBuildSupportEffectResolver(
        gear_set_effect_variant_resolver=GearSetEffectVariantResolver(
            GearSetRepository(db_path)
        )
    )

    registry = resolver.resolve(
        build,
        active_bar=BarId.FRONT,
    )

    major_slayer = [
        effect
        for effect in registry.all()
        if effect.name == "major_slayer"
    ]

    assert len(major_slayer) == 1
    assert major_slayer[0].target_count == 5
    assert major_slayer[0].range == 28    