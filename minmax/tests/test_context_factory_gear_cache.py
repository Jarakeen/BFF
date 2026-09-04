from models.build_model import GearSlot, PlayerBuild

from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearCalculationInputs


class _FakeGearResolver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def resolve(self, build: PlayerBuild, *, active_bar: str = "front") -> GearCalculationInputs:
        self.calls.append((str(build.Food or ""), str(active_bar or "front")))
        return GearCalculationInputs(applied_effect_count=len(self.calls))


def _factory() -> tuple[BuildCalculationContextFactory, _FakeGearResolver]:
    factory = BuildCalculationContextFactory()
    resolver = _FakeGearResolver()
    factory.gear_resolver = resolver
    return factory, resolver


def _build() -> PlayerBuild:
    build = PlayerBuild(
        Mundus="The Ritual",
        Food="Witchmother's Potent Brew",
        FrontBarWeapon=GearSlot(Set="Spell Power Cure", WeaponType="Restoration Staff"),
        BackBarWeapon=GearSlot(Set="Spell Power Cure", WeaponType="Ice Staff"),
        Necklace=GearSlot(Set="Pillager's Profit", Trait="Infused", Quality="Gold"),
        Ring1=GearSlot(Set="Pillager's Profit", Trait="Infused", Quality="Gold"),
        Ring2=GearSlot(Set="Pillager's Profit", Trait="Infused", Quality="Gold"),
    )
    build.Armor["Chest"].update(
        {
            "Set": "Spell Power Cure",
            "Trait": "Divines",
            "Enchant": "Max Magicka",
            "Quality": "Gold",
            "EnchantTier": "Truly Superb",
            "Level": "CP160",
            "Weight": "Light",
        }
    )
    return build


def test_gear_cache_reuses_equipment_across_food_mundus_and_skill_changes() -> None:
    factory, resolver = _factory()
    baseline = _build()
    candidate = PlayerBuild.from_dict(baseline.to_dict())
    candidate.Food = "Ghastly Eye Bowl"
    candidate.Mundus = "The Atronach"
    candidate.FrontBarSkills[0] = "Combat Prayer"

    first = factory._resolved_gear_inputs(baseline, active_bar="front")
    second = factory._resolved_gear_inputs(candidate, active_bar="front")

    assert first is second
    assert resolver.calls == [("Witchmother's Potent Brew", "front")]


def test_gear_cache_invalidates_when_armor_changes() -> None:
    factory, resolver = _factory()
    baseline = _build()
    candidate = PlayerBuild.from_dict(baseline.to_dict())
    candidate.Armor["Chest"]["Trait"] = "Infused"

    first = factory._resolved_gear_inputs(baseline, active_bar="front")
    second = factory._resolved_gear_inputs(candidate, active_bar="front")

    assert first is not second
    assert first.applied_effect_count == 1
    assert second.applied_effect_count == 2
    assert len(resolver.calls) == 2


def test_gear_cache_invalidates_for_active_bar_and_weapon_changes() -> None:
    factory, resolver = _factory()
    build = _build()

    front = factory._resolved_gear_inputs(build, active_bar="front")
    back = factory._resolved_gear_inputs(build, active_bar="back")
    changed = PlayerBuild.from_dict(build.to_dict())
    changed.FrontBarWeapon.Set = "Master Architect"
    changed_front = factory._resolved_gear_inputs(changed, active_bar="front")

    assert front is not back
    assert front is not changed_front
    assert len(resolver.calls) == 3


def test_gear_cache_is_scoped_to_factory_instance() -> None:
    build = _build()
    first_factory, first_resolver = _factory()
    second_factory, second_resolver = _factory()

    first = first_factory._resolved_gear_inputs(build, active_bar="front")
    second = second_factory._resolved_gear_inputs(build, active_bar="front")

    assert first is not second
    assert len(first_resolver.calls) == 1
    assert len(second_resolver.calls) == 1
