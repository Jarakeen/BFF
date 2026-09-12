from types import SimpleNamespace

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationSavedBuildWeaponAttackEvaluationService,
)


class _Adapter:
    def adapt(self, _build, *, character_id=None):
        assert character_id == "char-1"
        return SavedBuildAdaptation(
            CharacterBuild(
                name="Corpsebuster DD",
                character_class=CharacterClass.NECROMANCER,
                role=Role.DD,
                character_id=character_id,
            ),
            (
                "front main hand: weapon enchantment label not found in WeaponEnchantmentRepository: Flame",
                "front off hand: weapon enchantment label not found in WeaponEnchantmentRepository: Poison",
                "front slot 3: Magical Banner is not eligible for this saved build.",
                "back main hand: legacy weapon type is ambiguous and will not be guessed: Two-Handed",
                "back slot 3: Magical Banner is not eligible for this saved build.",
            ),
        )


def _trace(value):
    return SimpleNamespace(final_value=value)


def _context(bar):
    return SimpleNamespace(
        active_bar=bar,
        core_state=SimpleNamespace(
            derived={
                StatId.MAX_MAGICKA: _trace(30000.0),
                StatId.MAX_STAMINA: _trace(30000.0),
                StatId.WEAPON_DAMAGE: _trace(5000.0),
                StatId.SPELL_DAMAGE: _trace(5000.0),
                StatId.PHYSICAL_PENETRATION: _trace(7000.0),
                StatId.SPELL_PENETRATION: _trace(7000.0),
                StatId.CRITICAL_DAMAGE: _trace(0.5),
                StatId.CRITICAL_CHANCE: _trace(0.4),
            }
        ),
        dd_exploiter_bonus=0.0,
    )


class _StaticContext:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="char-1")
    contexts = (_context("front"), _context("back"))


def _weapon(weapon_type):
    return GearSlot(Set="Test", WeaponType=weapon_type, Quality="Gold", Level="CP160")


def test_weapon_attack_structure_ignores_skill_and_enchant_diagnostics_but_not_ambiguous_weapon_identity():
    build = PlayerBuild(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role="DD",
        EsoClass="Necromancer",
        FrontBarWeapon=_weapon("Dagger"),
        FrontBarOffHand=_weapon("Dagger"),
        BackBarWeapon=_weapon("Two-Handed"),
    )
    service = RotationSavedBuildWeaponAttackEvaluationService(
        database_path="unused.db",
        build_adapter=_Adapter(),  # type: ignore[arg-type]
    )

    result = service.resolve(player_build=build, static_context=_StaticContext())

    assert result.resolved is True
    assert result.unresolved == ()
    assert result.build is not None
    assert result.build.front_bar is not None
    assert result.build.front_bar.main_hand.weapon_type is WeaponType.DAGGER
    assert result.build.front_bar.off_hand is not None
    assert result.build.front_bar.off_hand.weapon_type is WeaponType.DAGGER
    assert result.build.back_bar is None
    assert result.evaluation_for("front") is not None
    assert result.evaluation_for("back") is not None
