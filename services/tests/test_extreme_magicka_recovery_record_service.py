from __future__ import annotations

import math

from services.extreme_magicka_recovery_record_service import ExtremeMagickaRecoveryRecordService
from services.extreme_record_result import ExtremeRecordProofStatus


def test_closed_magicka_recovery_record_is_globally_proven() -> None:
    result = ExtremeMagickaRecoveryRecordService.record()

    assert result.objective_key == "magicka_recovery"
    assert result.proof_status is ExtremeRecordProofStatus.PROVEN
    assert result.raw_value == 19492.945
    assert math.ceil(result.raw_value) == 19493
    assert result.globally_proven is True
    assert result.search_coverage.denominator_proven is True
    assert result.search_coverage.omitted == ()
    assert result.unresolved == ()
    assert result.ceiling_threats == ()


def test_published_witness_preserves_closed_magicka_recovery_constraints() -> None:
    result = ExtremeMagickaRecoveryRecordService.record()
    witness = result.winning_build

    assert witness["record_kind"] == "theoretical_contextual_maximum"
    assert witness["game_update"] == "U50"
    assert witness["race"] == "Breton"
    assert witness["class_lines"] == (
        "Animal Companions",
        "Curative Runeforms",
        "Shadow",
    )
    assert witness["active_bar"] == {
        "Animal Companions": 1,
        "Support": 3,
        "Minor Intellect carrier": "Arcanist's Domain",
        "Mages Guild": 0,
    }
    assert witness["armor_weight"] == "Light"
    assert witness["armor_traits"] == {"Divines": 7}
    assert witness["mundus"] == "The Atronach"
    assert witness["named_sets"] == (
        ("Robes of Alteration Mastery", 3),
        ("Hiti's Hearth", 3),
        ("Arkay's Charity", 3),
        ("Shadowrend", 1),
        ("Chokethorn", 1),
        ("Torc of Tonal Constancy", 1),
    )
    assert witness["same_build_max_magicka"] == 26924.736
    assert witness["pre_percent_recovery"] == 5184.294
    assert witness["standing_recovery_percent"] == 126.0
    assert witness["contextual_recovery_percent"] == 150.0
    assert witness["total_recovery_percent"] == 276.0
    assert witness["eso_display_value"] == 19493


def test_record_keeps_runtime_and_external_conditions_explicit() -> None:
    result = ExtremeMagickaRecoveryRecordService.record()

    assert any("Torc of Tonal Constancy" in item for item in result.runtime_prerequisites)
    assert any("Continuous Attack" in item for item in result.runtime_prerequisites)
    assert any("Major Intellect" in item for item in result.self_provided_conditions)
    assert result.external_conditions == ("Emperor Domination at six Home Keeps",)
    assert ExtremeMagickaRecoveryRecordService.supports("magicka_recovery") is True
    assert ExtremeMagickaRecoveryRecordService.supports("health_recovery") is False
