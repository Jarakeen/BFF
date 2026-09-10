import sqlite3
from pathlib import Path

import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from minmax.role import Role
from minmax.support_effect_category import SupportEffectCategory
from services.rotation_build_effect_duration_service import RotationBuildEffectDurationService


def _serpents_disdain_piece() -> ArmorPiece:
    return ArmorPiece(
        slot=GearSlot.CHEST,
        category=GearPieceCategory.SET_PIECE,
        set_id="641",
        effects=(
            EffectVariant(
                name="status_effect_duration_increase",
                layer=EffectLayer.PASSIVE,
                source="Serpent's Disdain (5)",
                magnitude=16.0,
                category=SupportEffectCategory.OTHER,
            ),
        ),
    )


def _status_effect() -> EffectVariant:
    return EffectVariant(
        name="chilled",
        layer=EffectLayer.PROC,
        source="verified status-effect source",
        duration=4.0,
        category=SupportEffectCategory.STATUS,
    )


def _jorvulds_db(path: Path) -> None:
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
            """
        )
        db.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (?, ?, ?, ?)",
            (9001, "Jorvuld's Guidance", "standard", 5),
        )
        db.execute(
            "INSERT INTO gear_set_bonus(id, set_id, piece_count, description) VALUES (?, ?, ?, ?)",
            (9002, 9001, 5, "verified Jorvuld's Guidance five-piece row"),
        )


def _jorvulds_armor() -> tuple[ArmorPiece, ...]:
    slots = (
        GearSlot.HEAD,
        GearSlot.SHOULDERS,
        GearSlot.CHEST,
        GearSlot.HANDS,
        GearSlot.WAIST,
    )
    return tuple(
        ArmorPiece(
            slot=slot,
            category=GearPieceCategory.SET_PIECE,
            set_id="9001",
        )
        for slot in slots
    )


@pytest.mark.parametrize("role", [Role.HEALER, Role.TANK, Role.DD])
def test_build_duration_resolution_is_role_neutral(role: Role) -> None:
    build = CharacterBuild(
        name="duration-test",
        character_class=CharacterClass.WARDEN,
        role=role,
        armor=(_serpents_disdain_piece(),),
    )

    resolved = RotationBuildEffectDurationService().resolve(
        build=build,
        active_bar=BarId.FRONT,
        effect=_status_effect(),
    )

    assert resolved.base_duration_seconds == pytest.approx(4.0)
    assert resolved.effective_duration_seconds == pytest.approx(20.0)
    assert resolved.unresolved == ()
    assert resolved.applied_modifiers[0].source == "Serpent's Disdain (5)"


def test_build_without_duration_modifier_keeps_canonical_effect_duration() -> None:
    build = CharacterBuild(
        name="plain-build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
    )

    resolved = RotationBuildEffectDurationService().resolve(
        build=build,
        active_bar=BarId.BACK,
        effect=_status_effect(),
    )

    assert resolved.effective_duration_seconds == pytest.approx(4.0)
    assert resolved.applied_modifiers == ()
    assert resolved.unresolved == ()


def test_equipped_jorvulds_set_identity_extends_major_slayer_without_attached_piece_effects(
    tmp_path: Path,
) -> None:
    database = tmp_path / "eso.db"
    _jorvulds_db(database)
    build = CharacterBuild(
        name="rojo-build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=_jorvulds_armor(),
    )
    major_slayer = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Roaring Opportunist",
        duration=12.0,
        category=SupportEffectCategory.BUFF,
    )

    resolved = RotationBuildEffectDurationService(database_path=database).resolve(
        build=build,
        active_bar=BarId.FRONT,
        effect=major_slayer,
    )

    assert resolved.base_duration_seconds == pytest.approx(12.0)
    assert resolved.effective_duration_seconds == pytest.approx(16.8)
    assert resolved.unresolved == ()
    assert len(resolved.applied_modifiers) == 1
    assert resolved.applied_modifiers[0].source == "Jorvuld's Guidance (5)"
    assert resolved.applied_modifiers[0].seconds == pytest.approx(4.8)
