from pathlib import Path
import json
import subprocess
import sys


def test_cli_writes_separate_reviewed_restart_fixture(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "review_phase13_healer_refresh_policies.py"
    output = tmp_path / "reviewed_refresh.json"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--approve-restart",
            "Illustrious Healing:1",
            "--approve-restart",
            "Energy Orb:1",
            "--game-version",
            "U50",
            "--review-note",
            "explicit human review",
            "--evidence-source",
            "recipient-aware audit FPy6Tc9BzwQNbfVK fights 6,27,41",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["review_status"] == "reviewed"
    assert [item["source_name"] for item in payload["policies"]] == [
        "Illustrious Healing",
        "Energy Orb",
    ]
    assert all(item["refresh_policy"] == "restart" for item in payload["policies"])
    assert "Boundary: separate reviewed fixture" in result.stdout


def test_cli_help_runs_from_tools_path():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "review_phase13_healer_refresh_policies.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--approve-restart" in result.stdout
