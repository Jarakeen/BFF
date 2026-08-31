import sqlite3

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_layer import BarId
from minmax.character_build.gear_piece import (
    ArmorPiece,
    GearPieceCategory,
    GearSlot,
)
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.support_effect_resolver import (
    CharacterBuildSupportEffectResolver,
    equipped_gear_set_counts,
)
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.character_build.character_class import CharacterClass
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.role import Role


MASTER_ARCHITECT_ID = "332"
OTHER_SET_ID = "999"


def _piece(slot, set_id=MASTER_ARCHITECT_ID):
    return ArmorPiece(
        slot=slot,
        category=GearPieceCategory.SET_PIECE,
        set_id=set_id,
    )


def _slots():
    return tuple(
        SlottedSkill(
            skill_id=f"test_skill_{i}",
            skill_line_id="animal_companions",
            is_ultimate=(i == 5),
        )
        for i in range(6)
    )


def _bar(bar_id, weapon_type, set_id):
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(
            weapon_type=weapon_type,
            set_id=set_id,
        ),
        off_hand=None,
        slots=_slots(),
    )


def _build():
    return CharacterBuild(
        name="Test Warden",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(
            _piece(GearSlot.HEAD),
            _piece(GearSlot.CHEST),
            _piece(GearSlot.LEGS),
        ),
        front_bar=_bar(
            BarId.FRONT,
            WeaponType.RESTORATION_STAFF,
            MASTER_ARCHITECT_ID,
        ),
        back_bar=_bar(
            BarId.BACK,
            WeaponType.FROST_STAFF,
            OTHER_SET_ID,
        ),
    )


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


def test_active_bar_staff_counts_as_two_set_pieces():
    build = _build()

    assert equipped_gear_set_counts(
        build,
        active_bar=BarId.FRONT,
    ) == {MASTER_ARCHITECT_ID: 5}


def test_inactive_bar_weapon_does_not_contribute():
    build = _build()

    assert equipped_gear_set_counts(
        build,
        active_bar=BarId.BACK,
    ) == {
        MASTER_ARCHITECT_ID: 3,
        OTHER_SET_ID: 2,
    }


def test_three_body_pieces_plus_active_staff_resolve_five_piece_bonus(tmp_path):
    db_path = tmp_path / "test.db"
    _make_db(db_path)

    resolver = CharacterBuildSupportEffectResolver(
        gear_set_effect_variant_resolver=GearSetEffectVariantResolver(
            GearSetRepository(db_path)
        )
    )

    registry = resolver.resolve(
        _build(),
        active_bar=BarId.FRONT,
    )

    major_slayer = [
        effect
        for effect in registry.all()
        if effect.name == "major_slayer"
    ]

    assert len(major_slayer) == 1
