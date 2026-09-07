from models.build_model import GearSlot, PlayerBuild
from minmax.healer_wait_decision_provider import (
    HealerHeavyAttackCandidate,
    HealerWaitDecisionProvider,
)
from minmax.heavy_attack_opportunity import (
    HeavyAttackOpportunityEvidence,
    HeavyAttackPurpose,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.runtime_healer_wait_decision_provider import RuntimeHealerWaitDecisionProvider
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationSupport,
)


def _armor_set(build: PlayerBuild, name: str, pieces: int) -> None:
    for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")[:pieces]:
        build.Armor[slot]["Set"] = name


def _ro_healer() -> PlayerBuild:
    build = PlayerBuild(
        Name="Synthetic Warden",
        BuildName="RO Healer",
        EsoClass="Warden",
        Role="Healer",
        FrontBarWeapon=GearSlot(
            Set="Roaring Opportunist",
            WeaponType="Restoration Staff",
        ),
        BackBarWeapon=GearSlot(WeaponType="Ice Staff"),
    )
    _armor_set(build, "Roaring Opportunist", 3)
    return build


def test_ro_healer_build_gets_runtime_required_heavy_provider_automatically() -> None:
    support = RotationGenerationSupport()

    provider = support._wait_decision(
        build=_ro_healer(),
        request=RotationGenerationRequest(required_heavy_channel_seconds=1.8),
    )

    assert isinstance(provider, RuntimeHealerWaitDecisionProvider)
    assert provider.required_window_seconds == 1.8
    assert [item.name for item in provider.incentives] == ["Roaring Opportunist"]


def test_non_ro_healer_does_not_auto_schedule_healing_or_recovery_value_heavies() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        EsoClass="Warden",
        Role="Healer",
        FrontBarWeapon=GearSlot(WeaponType="Restoration Staff"),
        BackBarWeapon=GearSlot(WeaponType="Ice Staff"),
    )

    provider = RotationGenerationSupport()._wait_decision(
        build=build,
        request=RotationGenerationRequest(),
    )

    assert provider is None


def test_manual_heavy_candidates_override_auto_required_heavy_discovery() -> None:
    manual = HealerHeavyAttackCandidate(
        bar="front",
        evidence=HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
            requirement_name="Manual Requirement",
            available_window_seconds=2.0,
            required_window_seconds=1.8,
        ),
    )

    provider = RotationGenerationSupport()._wait_decision(
        build=_ro_healer(),
        request=RotationGenerationRequest(heavy_attack_candidates=(manual,)),
    )

    assert isinstance(provider, HealerWaitDecisionProvider)
    assert provider.candidates == (manual,)


def test_auto_required_heavy_discovery_can_be_disabled_explicitly() -> None:
    provider = RotationGenerationSupport()._wait_decision(
        build=_ro_healer(),
        request=RotationGenerationRequest(auto_required_heavy_attacks=False),
    )

    assert provider is None
