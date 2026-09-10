from pathlib import Path
import subprocess
import sys


def test_consensus_audit_cli_can_be_executed_directly_from_tools_path():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "audit_phase13_healer_runtime_observation_consensus.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--observations" in result.stdout
    assert "--first-tick-spread-tolerance" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
