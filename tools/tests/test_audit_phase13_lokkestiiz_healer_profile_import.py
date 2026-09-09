from pathlib import Path
import runpy


def test_phase13_lokkestiiz_audit_runs_as_direct_script_import_path() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "tools" / "audit_phase13_lokkestiiz_healer_profile.py"
    namespace = runpy.run_path(str(script), run_name="phase13_lokkestiiz_audit_test")
    assert "main" in namespace
