from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_progression import CharacterProgression
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.saved_build_capability_service import SavedBuildCapabilityService


def test_active_set_counts_use_only_active_weapon_bar_and_two_piece_staff():
    build = PlayerBuild()
    build.Armor["Head"]["Set"] = "Set A"
    build.Necklace.Set = "Set A"
    build.FrontBarWeapon.Set = "Set A"
    build.FrontBarWeapon.WeaponType = "Restoration Staff"
    build.BackBarWeapon.Set = "Set B"
    build.BackBarWeapon.WeaponType = "Ice Staff"

    assert SavedBuildCapabilityService._active_set_counts(build, "front") == {"Set A": 4}
    assert SavedBuildCapabilityService._active_set_counts(build, "back") == {
        "Set A": 2,
        "Set B": 2,
    }


def test_intentional_potion_static_warning_is_not_a_genuine_gap():
    unresolved, boundaries = SavedBuildCapabilityService._partition_context_messages(
        (
            "Potion selected; activation/uptime is not part of static build state: spell power",
            "real unresolved mechanic",
        )
    )

    assert unresolved == ["real unresolved mechanic"]
    assert boundaries == [
        "Potion selected; activation/uptime is not part of static build state: spell power"
    ]


class _Progression:
    def resolve(self, _build):
        return SimpleNamespace(
            character_id="char-1",
            progression=CharacterProgression(passive_ranks={}, passive_cp_points={}),
            unresolved=(),
        )


class _ContextFactory:
    def build(self, **_kwargs):
        return SimpleNamespace(
            unresolved_gear_effects=(
                "Potion selected; activation/uptime is not part of static build state: spell power",
            )
        )


class _PotionRepository:
    def __init__(self, effect):
        self.effect = effect

    def resolve(self, _name):
        return SimpleNamespace(effects=(self.effect,), unresolved=())


def test_audit_keeps_consumable_conditional_and_not_standing_unresolved():
    potion_effect = EffectVariant(
        name="increase_spell_power",
        layer=EffectLayer.CONSUMABLE,
        source="Potion: spell power",
        trigger="potion_use",
        condition="selected potion available; activation and uptime are not assumed",
        target_type=SupportTargetType.SELF,
        category=SupportEffectCategory.BUFF,
    )
    service = SavedBuildCapabilityService.__new__(SavedBuildCapabilityService)
    service.progression = _Progression()
    service.context_factory = _ContextFactory()
    service.potions = _PotionRepository(potion_effect)
    service._skill_variants = lambda *_args: []
    service._gear_variants = lambda *_args: []

    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Potion="spell power")
    result = service.audit_build(build)

    assert result.character_id == "char-1"
    assert result.unresolved == ()
    assert result.resolved
    assert result.resolved_sources == ("potion:availability",)
    assert result.resolved_effects == (potion_effect,)
    assert result.conditional_sources == ("Potion: spell power",)
    assert "Potion availability resolved without standing uptime: spell power" in result.boundaries
