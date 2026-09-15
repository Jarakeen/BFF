from pathlib import Path

from services.extreme_health_recovery_record_service import ExtremeHealthRecoveryRecordService
from ui import extreme_health_recovery_record_support
from ui import application_extreme_optimization_bootstrap


def test_health_recovery_record_payload_is_projected_from_canonical_record() -> None:
    record = ExtremeHealthRecoveryRecordService.record()
    payload = extreme_health_recovery_record_support._display_payload()

    assert payload["value"] == f"{record.winning_build['eso_display_value']:,.0f}"
    assert "PROVEN" in payload["context"]
    assert "U50" in payload["context"]
    assert "Theoretical Stochastic Maximum" in payload["context"]
    assert "Khajiit" in payload["setup"]
    assert "The Steed" in payload["setup"]
    assert "Fresh Dragon's-Tongue Ale" in payload["setup"]
    assert "Beekeeper's Gear 5pc" in payload["gear"]
    assert "Adamant Lurker 5pc" in payload["gear"]
    assert "Baron Zaudrus 2pc" in payload["gear"]
    assert "Decisive Inferno Staff" in payload["gear"]
    assert "not a deterministic gameplay claim" in payload["prerequisite"]
    assert "Emperor Domination at six Home Keeps" in payload["external"]


def test_extreme_lab_installs_health_recovery_record_support() -> None:
    source = Path(application_extreme_optimization_bootstrap.__file__).read_text(encoding="utf-8")

    assert "from ui.extreme_health_recovery_record_support import install as install_extreme_health_recovery_record_support" in source
    assert "install_extreme_health_recovery_record_support()" in source
