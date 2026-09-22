from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_progression import CharacterProgression
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from models.build_model import ChampionPointEntry, GearSlot, PlayerBuild
from services.build_service import BuildService
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



def test_active_set_counts_include_explicit_offhand_weapon_piece():
    build = PlayerBuild()
    build.Armor["Head"]["Set"] = "Set A"
    build.FrontBarWeapon.Set = "Set A"
    build.FrontBarWeapon.WeaponType = "Dagger"
    build.FrontBarOffHand.Set = "Set A"
    build.FrontBarOffHand.WeaponType = "Axe"

    assert SavedBuildCapabilityService._active_set_counts(build, "front") == {
        "Set A": 3,
    }


def test_active_set_counts_treat_bow_as_two_set_pieces():
    build = PlayerBuild()
    build.Armor["Head"]["Set"] = "Set A"
    build.Armor["Chest"]["Set"] = "Set A"
    build.Armor["Legs"]["Set"] = "Set A"
    build.FrontBarWeapon.Set = "Set A"
    build.FrontBarWeapon.WeaponType = "Bow"

    assert SavedBuildCapabilityService._active_set_counts(build, "front") == {
        "Set A": 5,
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


def test_service_defaults_to_phase5_canonical_context_factory(tmp_path):
    service = SavedBuildCapabilityService(
        BuildService(tmp_path / "builds.json"),
        tmp_path / "eso.db",
    )

    assert isinstance(service.context_factory, Phase5BuildCalculationContextFactory)


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


def test_audit_keeps_consumable_conditional_and_not_standing_unresolved(tmp_path):
    potion_effect = EffectVariant(
        name="increase_spell_power",
        layer=EffectLayer.CONSUMABLE,
        source="Potion: spell power",
        trigger="potion_use",
        condition="selected potion available; activation and uptime are not assumed",
        target_type=SupportTargetType.SELF,
        category=SupportEffectCategory.BUFF,
    )
    service = SavedBuildCapabilityService(
        BuildService(tmp_path / "builds.json"),
        tmp_path / "eso.db",
        context_factory=_ContextFactory(),
        progression=_Progression(),
        skills=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        gear=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        potions=_PotionRepository(potion_effect),
    )
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


def test_effect_variant_resolution_includes_verified_dynamic_champion_point_effects(tmp_path):
    cp_effect = EffectVariant(
        name="damage_shield",
        layer=EffectLayer.PROC,
        source="Champion Point: From the Brink",
        trigger="on_heal_target_below_25_percent_health",
    )

    class _ChampionPoints:
        def resolve(self, name, points):
            assert name == "From the Brink"
            assert points == 50
            return (cp_effect,), ()

    service = SavedBuildCapabilityService(
        BuildService(tmp_path / "builds.json"),
        tmp_path / "eso.db",
        skills=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        gear=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        potions=SimpleNamespace(resolve=lambda *_args, **_kwargs: SimpleNamespace(effects=(), unresolved=())),
        champion_point_effect_resolver=_ChampionPoints(),
    )
    service._skill_component = lambda _build, _bar: SimpleNamespace(
        effects=(), unresolved=(), boundaries=()
    )
    service._gear_component = lambda _build, _bar: SimpleNamespace(
        effects=(), unresolved=(), boundaries=()
    )

    result = service.resolve_effect_variants(
        PlayerBuild(
            Name="Generated",
            BuildName="Candidate",
            ChampionPoints=[ChampionPointEntry(Name="From the Brink", Points="50")],
        )
    )

    assert result.resolved is True
    assert result.effects == (cp_effect,)


def test_effect_variant_resolution_fails_closed_on_invalid_champion_point_allocation(tmp_path):
    service = SavedBuildCapabilityService(
        BuildService(tmp_path / "builds.json"),
        tmp_path / "eso.db",
        skills=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        gear=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        potions=SimpleNamespace(resolve=lambda *_args, **_kwargs: SimpleNamespace(effects=(), unresolved=())),
        champion_point_effect_resolver=SimpleNamespace(resolve=lambda *_args: ((), ())),
    )
    service._skill_component = lambda _build, _bar: SimpleNamespace(
        effects=(), unresolved=(), boundaries=()
    )
    service._gear_component = lambda _build, _bar: SimpleNamespace(
        effects=(), unresolved=(), boundaries=()
    )

    result = service.resolve_effect_variants(
        PlayerBuild(
            ChampionPoints=[ChampionPointEntry(Name="From the Brink", Points="banana")]
        )
    )

    assert result.resolved is False
    assert result.unresolved == (
        "Champion Point entry has invalid allocation: From the Brink: banana",
    )


def test_effect_variant_resolution_does_not_require_saved_character_progression(tmp_path):
    skill_effect = EffectVariant(
        name="skill_proc",
        layer=EffectLayer.PROC,
        source="Skill A",
        trigger="damage_dealt",
    )
    gear_effect = EffectVariant(
        name="gear_proc",
        layer=EffectLayer.PROC,
        source="Set A",
        trigger="light_attack",
    )
    potion_effect = EffectVariant(
        name="potion_buff",
        layer=EffectLayer.CONSUMABLE,
        source="Potion: spell power",
        trigger="potion_use",
    )

    class _ForbiddenProgression:
        def resolve(self, _build):
            raise AssertionError("capability-only effect resolution must not load saved progression")

    class _ForbiddenContext:
        def build(self, **_kwargs):
            raise AssertionError("capability-only effect resolution must not build static context")

    service = SavedBuildCapabilityService(
        BuildService(tmp_path / "builds.json"),
        tmp_path / "eso.db",
        context_factory=_ForbiddenContext(),
        progression=_ForbiddenProgression(),
        skills=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        gear=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        potions=_PotionRepository(potion_effect),
    )
    service._skill_component = lambda _build, bar: SimpleNamespace(
        effects=(skill_effect,) if bar == "front" else (),
        unresolved=(),
        boundaries=(),
    )
    service._gear_component = lambda _build, bar: SimpleNamespace(
        effects=(gear_effect,) if bar == "front" else (),
        unresolved=(),
        boundaries=(),
    )

    result = service.resolve_effect_variants(
        PlayerBuild(Name="Generated", BuildName="Candidate", Potion="spell power")
    )

    assert result.resolved is True
    assert result.effects == (skill_effect, gear_effect, potion_effect)
    assert result.unresolved == ()
    assert "Potion availability resolved without standing uptime: spell power" in result.boundaries


class _CrusherRepository:
    def find_item_ids_by_label(self, label):
        assert label == "Crushing"
        return (26845,)


class _CrusherEffects:
    def resolve_effects(
        self,
        item_id,
        *,
        weapon_trait=None,
        weapon_quality=None,
    ):
        assert item_id == 26845
        assert weapon_trait == "Infused"
        assert weapon_quality == "Legendary"
        return [
            CombatEffect(
                effect_type="physical_spell_resistance_reduction",
                value=2108.6,
                source="Crusher Enchantment",
                unit=EffectUnit.FLAT,
                target="target",
                duration_value=5.0,
                duration_unit="seconds",
            )
        ]


def test_effect_variant_resolution_includes_canonical_crusher_capability(tmp_path):
    service = SavedBuildCapabilityService(
        BuildService(tmp_path / "builds.json"),
        tmp_path / "eso.db",
        skills=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        gear=SimpleNamespace(resolve=lambda *_args, **_kwargs: ()),
        potions=SimpleNamespace(
            resolve=lambda *_args, **_kwargs: SimpleNamespace(
                effects=(),
                unresolved=(),
            )
        ),
        weapon_enchantment_repository=_CrusherRepository(),
        weapon_enchantment_effect_service=_CrusherEffects(),
    )
    service._skill_component = lambda _build, _bar: SimpleNamespace(
        effects=(), unresolved=(), boundaries=()
    )
    service._gear_component = lambda _build, _bar: SimpleNamespace(
        effects=(), unresolved=(), boundaries=()
    )

    build = PlayerBuild(
        Name="Generated",
        BuildName="Crusher Candidate",
        FrontBarWeapon=GearSlot(
            WeaponType="Ice Staff",
            Enchant="Crushing",
            Trait="Infused",
            Quality="Legendary",
        ),
    )

    result = service.resolve_effect_variants(build)

    assert result.resolved is True
    assert len(result.effects) == 1
    crusher = result.effects[0]
    assert crusher.name == "physical_spell_resistance_reduction"
    assert crusher.source == "Crusher Enchantment"
    assert crusher.magnitude == 2108.6
    assert crusher.resistance_reduction == 2108.6
    assert crusher.duration == 5.0
    assert crusher.target_type == SupportTargetType.ENEMY
    assert crusher.active_bar.value == "front"
    assert crusher.trigger is None
    assert (
        "front main hand weapon enchantment runtime effect timing deferred: "
        "Crusher Enchantment"
    ) in result.boundaries
