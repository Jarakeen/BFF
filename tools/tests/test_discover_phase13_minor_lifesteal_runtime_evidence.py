from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "discover_phase13_minor_lifesteal_runtime_evidence.py"


def test_cli_bootstraps_repo_root_when_launched_as_script(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Minor Lifesteal" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
