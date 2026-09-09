from pathlib import Path
import subprocess
import sys


def test_phase13_lokkestiiz_audit_direct_cli_imports_project_modules() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "tools" / "audit_phase13_lokkestiiz_healer_profile.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
