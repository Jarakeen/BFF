from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_weapon_damage_record_service import (
    ExtremeWeaponDamageRecordService,
    WEAPON_DAMAGE_RECORD_VALUE,
    WEAPON_DAMAGE_WINNER,
)


def test_weapon_damage_closed_record_matches_reviewed_conditional_snapshot() -> None:
    service = ExtremeWeaponDamageRecordService()
    snapshot = service.snapshot()
    record = service.record()

    assert snapshot.named_gear_weapon_damage == 2193.0
    assert snapshot.pre_percent_reference == 8138.006
    assert round(snapshot.weapon_damage, 3) == WEAPON_DAMAGE_RECORD_VALUE

    assert record.objective_key == "weapon_damage"
    assert record.proof_status is ExtremeRecordProofStatus.CONDITIONAL
    assert record.conditionally_achievable is True
    assert record.globally_proven is False
    assert record.raw_value is not None
    assert round(record.raw_value, 3) == WEAPON_DAMAGE_RECORD_VALUE
    assert record.winning_build["sets"] == WEAPON_DAMAGE_WINNER
    assert record.search_coverage.denominator_proven is True
    assert record.search_coverage.omitted == ()
    assert record.search_coverage.candidates_screened == 79
    assert record.search_coverage.candidates_optimized == 79
    assert record.unresolved == ()
    assert record.ceiling_threats == ()


def test_weapon_damage_record_preserves_runtime_prerequisites() -> None:
    record = ExtremeWeaponDamageRecordService().record()

    joined = "\n".join(record.runtime_prerequisites)
    assert "25% Health" in joined
    assert "Off Balance" in joined
    assert "Bloodthirsty" in joined
    assert "Major Brutality" in joined
    assert "Font of Power" in joined
    assert "Calculated Defense" in joined
    assert "Six Sorcerer abilities" in joined
