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
