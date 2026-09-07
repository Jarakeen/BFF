from models.build_model import GearSlot, PlayerBuild
from minmax.healer_heavy_attack_build_discovery import HeavyAttackBuildIncentiveKind
from minmax.healer_recovery_heavy_pressure import HealerRecoveryHeavyPressure
from minmax.resource_costs import ResourceType
from minmax.runtime_healer_wait_decision_provider import RuntimeHealerWaitDecisionProvider
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


def _pressure_resolver(context):
    return HealerRecoveryHeavyPressure(
        resource=ResourceType.MAGICKA,
        time_seconds=context.time_seconds,
        current_amount=8000,
        maximum_amount=30000,
        resource_fraction=8000 / 30000,
        trigger_fraction=0.35,
        reserve_shortfall=0,
        recommended=True,
        reason="verified test recovery pressure",
    )


def _resto_healer() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        EsoClass="Warden",
        Role="Healer",
        FrontBarWeapon=GearSlot(WeaponType="Restoration Staff"),
        BackBarWeapon=GearSlot(WeaponType="Ice Staff"),
    )


def _ro_healer() -> PlayerBuild:
    build = _resto_healer()
    build.BuildName = "RO Healer"
    build.FrontBarWeapon.Set = "Roaring Opportunist"
    for slot in ("Head", "Shoulders", "Chest"):
        build.Armor[slot]["Set"] = "Roaring Opportunist"
    return build


def test_recovery_pressure_enables_discovered_resto_recovery_incentive() -> None:
    provider = RotationGenerationSupport()._wait_decision(
        build=_resto_healer(),
        request=RotationGenerationRequest(
            recovery_pressure_resolver=_pressure_resolver,
        ),
    )

    assert isinstance(provider, RuntimeHealerWaitDecisionProvider)
    assert provider.recovery_pressure_resolver is _pressure_resolver
    assert [item.name for item in provider.incentives] == ["Cycle of Life"]
    assert all(
        item.kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE
        for item in provider.incentives
    )


def test_ro_and_recovery_incentives_share_one_runtime_provider() -> None:
    provider = RotationGenerationSupport()._wait_decision(
        build=_ro_healer(),
        request=RotationGenerationRequest(
            recovery_pressure_resolver=_pressure_resolver,
        ),
    )

    assert isinstance(provider, RuntimeHealerWaitDecisionProvider)
    assert {item.kind for item in provider.incentives} == {
        HeavyAttackBuildIncentiveKind.RECOVERY_VALUE,
        HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
    }
    assert {item.name for item in provider.incentives} == {
        "Cycle of Life",
        "Roaring Opportunist",
    }


def test_recovery_pressure_does_not_auto_enable_non_healer_heavies() -> None:
    build = _resto_healer()
    build.Role = "Damage Dealer"

    provider = RotationGenerationSupport()._wait_decision(
        build=build,
        request=RotationGenerationRequest(
            recovery_pressure_resolver=_pressure_resolver,
        ),
    )

    assert provider is None
