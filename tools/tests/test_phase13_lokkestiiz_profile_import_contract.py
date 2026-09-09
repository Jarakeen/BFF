from pathlib import Path


def test_phase13_lokkestiiz_audit_declares_repo_root_bootstrap() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "tools" / "audit_phase13_lokkestiiz_healer_profile.py").read_text(encoding="utf-8")
    assert "sys.path" in text
    assert "Path(__file__).resolve().parents[1]" in text
