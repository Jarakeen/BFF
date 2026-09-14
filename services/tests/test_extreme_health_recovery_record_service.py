from __future__ import annotations

import math

from services.extreme_health_recovery_record_service import ExtremeHealthRecoveryRecordService
from services.extreme_record_result import ExtremeRecordProofStatus


def test_closed_health_recovery_record_is_globally_proven() -> None:
    result = ExtremeHealthRecoveryRecordService.record()

    assert result.objective_key == "health_recovery"
    assert result.proof_status is ExtremeRecordProofStatus.PROVEN
    assert result.raw_value == 22576.212
    assert math.ceil(result.raw_value) == 22577
    assert result.globally_proven is True
    assert result.search_coverage.denominator_proven is True
    assert result.search_coverage.omitted == ()
    assert result.unresolved == ()
    assert result.ceiling_threats == ()


def test_published_witness_preserves_closed_same_build_constraints() -> None:
    result = ExtremeHealthRecoveryRecordService.record()
    witness = result.winning_build

    assert witness["record_kind"] == "theoretical_stochastic_maximum"
    assert witness["game_update"] == "U50"
    assert witness["race"] == "Khajiit"
    assert witness["named_sets"] == (
        ("Beekeeper's Gear", 5),
        ("Adamant Lurker", 5),
        ("Baron Zaudrus", 2),
    )
    assert witness["weapon_type"] == "Inferno Staff"
    assert witness["weapon_trait"] == "Decisive"
    assert witness["same_build_max_magicka"] == 25932.744
    assert witness["eso_display_value"] == 22577


def test_record_keeps_stochastic_and_external_conditions_explicit() -> None:
    result = ExtremeHealthRecoveryRecordService.record()

    assert any("not a deterministic gameplay claim" in item for item in result.runtime_prerequisites)
    assert any("all-procs Decisive" in item for item in result.runtime_prerequisites)
    assert result.external_conditions == ("Emperor Domination at six Home Keeps",)
    assert ExtremeHealthRecoveryRecordService.supports("health_recovery") is True
    assert ExtremeHealthRecoveryRecordService.supports("max_health") is False
