from pathlib import Path
import subprocess
import sys

from tools.extract_phase13_healer_runtime_observation_candidates import build_parser


def test_parser_defaults_to_esologs_milliseconds():
    args = build_parser().parse_args(
        [
            "--raw",
            "raw.json",
            "--fight-id",
            "4",
            "--caster-id",
            "7",
            "--out",
            "candidates.json",
        ]
    )

    assert args.timestamp_unit == "milliseconds"
    assert args.db == "data/eso.db"
    assert args.game_version == "U50"


def test_cli_is_directly_executable_from_tools_path():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "tools" / "extract_phase13_healer_runtime_observation_candidates.py"),
            "--help",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--caster-id" in result.stdout
    assert "candidate" in result.stdout.casefold()
