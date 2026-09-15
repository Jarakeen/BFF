from pathlib import Path

from services.extreme_magicka_recovery_record_service import ExtremeMagickaRecoveryRecordService
from ui import extreme_magicka_recovery_record_support
from ui import application_extreme_optimization_bootstrap


def test_magicka_recovery_record_payload_is_projected_from_canonical_record() -> None:
    record = ExtremeMagickaRecoveryRecordService.record()
    payload = extreme_magicka_recovery_record_support._display_payload()

    assert payload["value"] == f"{record.winning_build['eso_display_value']:,.0f}"
    assert "PROVEN" in payload["context"]
    assert "U50" in payload["context"]
    assert "Theoretical Contextual Maximum" in payload["context"]
    assert "Breton" in payload["setup"]
    assert "Light" in payload["setup"]
    assert "The Atronach" in payload["setup"]
    assert "Crisp River's Ale" in payload["setup"]
    assert "Torc of Tonal Constancy 1pc" in payload["gear"]
    assert "Robes of Alteration Mastery 3pc" in payload["gear"]
    assert "Animal Companions + Curative Runeforms + Shadow" == payload["route"]
    assert "1 Animal Companions" in payload["bar"]
    assert "3 Support" in payload["bar"]
    assert "Arcanist's Domain" in payload["bar"]
    assert "all listed standing and contextual states" in payload["prerequisite"]
    assert "Emperor Domination at six Home Keeps" in payload["external"]


def test_extreme_lab_installs_magicka_recovery_record_support() -> None:
    source = Path(application_extreme_optimization_bootstrap.__file__).read_text(encoding="utf-8")

    assert "from ui.extreme_magicka_recovery_record_support import install as install_extreme_magicka_recovery_record_support" in source
    assert "install_extreme_magicka_recovery_record_support()" in source
