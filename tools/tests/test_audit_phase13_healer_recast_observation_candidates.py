from pathlib import Path
import subprocess
import sys

from tools.audit_phase13_healer_recast_observation_candidates import _next_phase_time


def test_next_phase_time_returns_first_old_stream_tick_after_recast():
    assert _next_phase_time(origin=10.0, first_offset=0.05, cadence=1.0, after=12.4) == 13.05


def test_cli_can_be_executed_directly_from_tools_path():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "audit_phase13_healer_recast_observation_candidates.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--reviewed-observations" in result.stdout
    assert "--fight-id" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
