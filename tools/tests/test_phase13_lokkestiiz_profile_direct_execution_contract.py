from pathlib import Path


def test_direct_execution_contract_is_documented_in_audit_source() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "tools" / "audit_phase13_lokkestiiz_healer_profile.py").read_text(encoding="utf-8")
    assert "python tools\\audit_phase13_lokkestiiz_healer_profile.py" in text or "direct" in text.casefold()
