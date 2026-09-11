from pathlib import Path
import json
import subprocess
import sys


def _script() -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root, repo_root / "tools" / "review_phase13_healer_refresh_policies.py"


def test_cli_writes_separate_reviewed_restart_fixture(tmp_path: Path):
    repo_root, script = _script()
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


def test_cli_can_preserve_existing_reviewed_policies_when_adding_new_approval(tmp_path: Path):
    repo_root, script = _script()
    output = tmp_path / "reviewed_refresh.json"
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "policies": [
                    {
                        "source_name": "Energy Orb",
                        "coefficient_number": 1,
                        "game_version": "U50",
                        "refresh_policy": "restart",
                        "provenance": ["earlier explicit review"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--preserve-existing",
            "--approve-restart",
            "Budding Seeds:2",
            "--game-version",
            "U50",
            "--review-note",
            "explicit Budding Seeds review",
            "--evidence-source",
            "recipient-aware audits PCBxhWranVctf8Q2 fight 8 and v16hzgGWTV7BZ48f fight 22",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [item["source_name"] for item in payload["policies"]] == [
        "Energy Orb",
        "Budding Seeds",
    ]
    assert payload["policies"][0]["provenance"] == ["earlier explicit review"]
    assert payload["policies"][1]["provenance"][0] == "explicit Budding Seeds review"
    assert "Preserved existing reviewed policies: 1" in result.stdout


def test_cli_preserve_existing_rejects_silent_replacement_of_reviewed_policy(tmp_path: Path):
    repo_root, script = _script()
    output = tmp_path / "reviewed_refresh.json"
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "review_status": "reviewed",
                "game_version": "U50",
                "policies": [
                    {
                        "source_name": "Budding Seeds",
                        "coefficient_number": 2,
                        "game_version": "U50",
                        "refresh_policy": "restart",
                        "provenance": ["earlier explicit review"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output",
            str(output),
            "--preserve-existing",
            "--approve-restart",
            "Budding Seeds:2",
            "--game-version",
            "U50",
            "--review-note",
            "replacement attempt",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_cli_help_runs_from_tools_path():
    repo_root, script = _script()

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--approve-restart" in result.stdout
    assert "--preserve-existing" in result.stdout
