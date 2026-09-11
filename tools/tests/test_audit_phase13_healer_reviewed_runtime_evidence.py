from pathlib import Path
import subprocess
import sys


def test_cli_can_be_executed_directly_from_tools_path():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "audit_phase13_healer_reviewed_runtime_evidence.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--runtime-observations" in result.stdout
    assert "--refresh-policies" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
