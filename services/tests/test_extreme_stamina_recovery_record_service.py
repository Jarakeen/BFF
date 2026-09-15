from __future__ import annotations

import math

from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_stamina_recovery_record_service import ExtremeStaminaRecoveryRecordService


def test_closed_stamina_recovery_record_is_globally_proven() -> None:
    result = ExtremeStaminaRecoveryRecordService.record()

    assert result.objective_key == "stamina_recovery"
    assert result.proof_status is ExtremeRecordProofStatus.PROVEN
    assert result.raw_value == 16957.086
    assert math.ceil(result.raw_value) == 16958
    assert result.globally_proven is True
    assert result.search_coverage.denominator_proven is True
    assert result.search_coverage.omitted == ()
    assert result.unresolved == ()
    assert result.ceiling_threats == ()


def test_published_witness_preserves_closed_stamina_recovery_constraints() -> None:
    result = ExtremeStaminaRecoveryRecordService.record()
    witness = result.winning_build

    assert witness["record_kind"] == "theoretical_contextual_maximum"
    assert witness["game_update"] == "U50"
    assert witness["race"] == "Bosmer"
    assert witness["class_lines"] == (
        "Animal Companions",
        "Curative Runeforms",
        "Shadow",
    )
    assert witness["active_bar"] == {
        "Animal Companions": 1,
        "Minor Endurance carrier": "Arcanist's Domain",
    }
    assert witness["armor_weight"] == "Medium"
    assert witness["armor_traits"] == {"Divines": 7}
    assert witness["mundus"] == "The Serpent"
    assert witness["named_sets"] == (
        ("Jailbreaker", 5),
        ("Coward's Gear", 5),
        ("Bloodspawn", 1),
        ("Torc of Tonal Constancy", 1),
    )
    assert witness["weapon_type"] == "Two-Handed Sword"
    assert witness["same_build_max_magicka"] == 17638.656
    assert witness["pre_percent_recovery"] == 4509.863
    assert witness["standing_recovery_percent"] == 96.0
    assert witness["contextual_recovery_percent"] == 180.0
    assert witness["total_recovery_percent"] == 276.0
    assert witness["eso_display_value"] == 16958


def test_record_keeps_runtime_and_external_conditions_explicit() -> None:
    result = ExtremeStaminaRecoveryRecordService.record()

    assert any("Torc of Tonal Constancy" in item for item in result.runtime_prerequisites)
    assert any("Battle Rush" in item for item in result.runtime_prerequisites)
    assert any("Continuous Attack" in item for item in result.runtime_prerequisites)
    assert any("Major Endurance" in item for item in result.self_provided_conditions)
    assert result.external_conditions == ("Emperor Domination at six Home Keeps",)
    assert ExtremeStaminaRecoveryRecordService.supports("stamina_recovery") is True
    assert ExtremeStaminaRecoveryRecordService.supports("magicka_recovery") is False
