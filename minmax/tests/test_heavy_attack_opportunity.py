from minmax.heavy_attack_opportunity import (
    HeavyAttackOpportunityEvidence,
    HeavyAttackPurpose,
    evaluate_heavy_attack_opportunity,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.resource_costs import ResourceType


def test_recovery_heavy_requires_low_relevant_resource() -> None:
    result = evaluate_heavy_attack_opportunity(
        HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.RECOVERY,
            needed_resource=ResourceType.MAGICKA,
            current_resource=8000,
            maximum_resource=30000,
            recovery_trigger_fraction=0.35,
            available_window_seconds=2.0,
            required_window_seconds=1.8,
        )
    )

    assert result.recommended is True
    assert result.purpose is HeavyAttackPurpose.RECOVERY


def test_recovery_heavy_is_not_used_when_resource_is_healthy() -> None:
    result = evaluate_heavy_attack_opportunity(
        HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.RECOVERY,
            needed_resource=ResourceType.MAGICKA,
            current_resource=24000,
            maximum_resource=30000,
            recovery_trigger_fraction=0.35,
            available_window_seconds=2.0,
            required_window_seconds=1.8,
        )
    )

    assert result.recommended is False
    assert "above recovery trigger" in result.reason


def test_required_effect_heavy_can_be_recommended_without_low_resource() -> None:
    result = evaluate_heavy_attack_opportunity(
        HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
            requirement_name="Roaring Opportunist",
            available_window_seconds=2.0,
            required_window_seconds=1.8,
        )
    )

    assert result.recommended is True
    assert result.purpose is HeavyAttackPurpose.REQUIRED_EFFECT
    assert "Roaring Opportunist" in result.reason
    assert result.resource_fraction is None


def test_required_effect_heavy_yields_to_higher_priority_action() -> None:
    result = evaluate_heavy_attack_opportunity(
        HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
            requirement_name="Roaring Opportunist",
            available_window_seconds=2.0,
            required_window_seconds=1.8,
            higher_priority_action_ready=True,
        )
    )

    assert result.recommended is False
    assert "higher-priority" in result.reason


def test_required_effect_heavy_rejects_unsafe_channel_window() -> None:
    result = evaluate_heavy_attack_opportunity(
        HeavyAttackOpportunityEvidence(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
            requirement_name="Warden heavy-attack buff",
            available_window_seconds=2.0,
            required_window_seconds=1.8,
            encounter_allows_channel=False,
        )
    )

    assert result.recommended is False
    assert "safe channel" in result.reason
