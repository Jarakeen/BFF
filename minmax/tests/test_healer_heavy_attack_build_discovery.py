from models.build_model import GearSlot, PlayerBuild
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    discover_healer_heavy_attack_build_incentives,
)


def _armor_set(build: PlayerBuild, name: str, pieces: int) -> None:
    for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")[:pieces]:
        build.Armor[slot]["Set"] = name


def test_restoration_staff_discovers_verified_heavy_passive_incentives() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="Healer",
        EsoClass="Warden",
        FrontBarWeapon=GearSlot(WeaponType="Restoration Staff"),
        BackBarWeapon=GearSlot(WeaponType="Ice Staff"),
    )

    incentives = discover_healer_heavy_attack_build_incentives(build)
    by_name = {(item.bar, item.name): item for item in incentives}

    essence = by_name[("front", "Essence Drain")]
    assert essence.kind is HeavyAttackBuildIncentiveKind.HEALING_VALUE
    assert essence.maximum_effect_duration_seconds == 4.0

    cycle = by_name[("front", "Cycle of Life")]
    assert cycle.kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE
    assert ("back", "Essence Drain") not in by_name


def test_active_five_piece_roaring_opportunist_is_required_on_that_bar() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="RO Healer",
        EsoClass="Warden",
        FrontBarWeapon=GearSlot(Set="Roaring Opportunist", WeaponType="Restoration Staff"),
        BackBarWeapon=GearSlot(Set="Other Set", WeaponType="Ice Staff"),
    )
    _armor_set(build, "Roaring Opportunist", 3)

    incentives = discover_healer_heavy_attack_build_incentives(build)
    roaring = [item for item in incentives if item.name == "Roaring Opportunist"]

    assert len(roaring) == 1
    assert roaring[0].bar == "front"
    assert roaring[0].kind is HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT
    assert roaring[0].recurrence_seconds == 22.0
    assert roaring[0].maximum_effect_duration_seconds == 12.0


def test_roaring_opportunist_is_not_claimed_without_five_active_pieces() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="Incomplete RO",
        EsoClass="Warden",
        FrontBarWeapon=GearSlot(Set="Roaring Opportunist", WeaponType="Restoration Staff"),
    )
    _armor_set(build, "Roaring Opportunist", 2)

    incentives = discover_healer_heavy_attack_build_incentives(build)

    assert not any(item.name == "Roaring Opportunist" for item in incentives)


def test_warden_lotus_is_discovered_as_runtime_conditional_healing_value() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="Lotus Healer",
        EsoClass="Warden",
        FrontBarWeapon=GearSlot(WeaponType="Restoration Staff"),
        BackBarWeapon=GearSlot(WeaponType="Ice Staff"),
    )
    build.FrontBarSkills = ["Lotus Blossom", "", "", "", "", ""]

    incentives = discover_healer_heavy_attack_build_incentives(build)
    lotus = [item for item in incentives if item.name == "Lotus Blossom"]

    assert {item.bar for item in lotus} == {"front", "back"}
    assert all(item.kind is HeavyAttackBuildIncentiveKind.HEALING_VALUE for item in lotus)
    assert all(item.requires_active_effect == "Lotus Blossom" for item in lotus)
