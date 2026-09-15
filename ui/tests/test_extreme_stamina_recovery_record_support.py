from pathlib import Path

from services.extreme_stamina_recovery_record_service import ExtremeStaminaRecoveryRecordService
from ui import extreme_optimization_support
from ui import extreme_stamina_recovery_record_support


def test_stamina_recovery_record_payload_is_projected_from_canonical_record() -> None:
    record = ExtremeStaminaRecoveryRecordService.record()
    payload = extreme_stamina_recovery_record_support._display_payload()

    assert payload["value"] == f"{record.winning_build['eso_display_value']:,.0f}"
    assert "PROVEN" in payload["context"]
    assert "U50" in payload["context"]
    assert "Theoretical Contextual Maximum" in payload["context"]
    assert "Bosmer" in payload["setup"]
    assert "Medium" in payload["setup"]
    assert "The Serpent" in payload["setup"]
    assert "Two-Handed Sword" in payload["setup"]
    assert "Hagraven's Tonic" in payload["setup"]
    assert "Torc of Tonal Constancy 1pc" in payload["gear"]
    assert "Jailbreaker 5pc" in payload["gear"]
    assert "Animal Companions + Curative Runeforms + Shadow" == payload["route"]
    assert "1 Animal Companions" in payload["bar"]
    assert "Arcanist's Domain" in payload["bar"]
    assert "all listed standing and contextual states" in payload["prerequisite"]
    assert "Emperor Domination at six Home Keeps" in payload["external"]


def test_extreme_lab_installs_stamina_recovery_record_support() -> None:
    source = Path(extreme_optimization_support.__file__).read_text(encoding="utf-8")

    assert "from ui.extreme_stamina_recovery_record_support import install as install_extreme_stamina_recovery_record_support" in source
    assert "install_extreme_stamina_recovery_record_support()" in source
