from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from services.esologs_event_interpreter import SemanticEventKind
from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationTarget,
)
from tools.extract_phase13_healer_runtime_observation_candidates import (
    _candidate_caster_rows,
    build_parser,
)


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


def test_parser_allows_caster_discovery_without_caster_or_output():
    args = build_parser().parse_args(
        [
            "--raw",
            "raw.json",
            "--fight-id",
            "4",
            "--list-casters",
        ]
    )

    assert args.list_casters is True
    assert args.caster_id is None
    assert args.out is None


def _event(source_id, ability_id, event_kind):
    return SimpleNamespace(
        source_id=source_id,
        ability_game_id=ability_id,
        event_kind=event_kind,
    )


def test_candidate_caster_rows_rank_broader_hot_coverage_first():
    targets = (
        RotationHealerEsoLogsObservationTarget("Hot One", 1, 101),
        RotationHealerEsoLogsObservationTarget("Hot Two", 1, 202),
    )
    events = (
        _event(10, 101, SemanticEventKind.CAST),
        _event(10, 101, SemanticEventKind.HEAL),
        _event(20, 101, SemanticEventKind.CAST),
        _event(20, 202, SemanticEventKind.CAST),
        _event(20, 202, SemanticEventKind.HEAL),
        _event(30, 999, SemanticEventKind.CAST),
    )

    rows = _candidate_caster_rows(events, targets)

    assert [row["source_id"] for row in rows] == [20, 10]
    assert rows[0]["abilities"] == ("Hot One", "Hot Two")
    assert rows[0]["casts"] == 2
    assert rows[0]["heals"] == 1


def test_candidate_caster_rows_accept_numeric_aliases_for_same_canonical_skill():
    targets = (
        RotationHealerEsoLogsObservationTarget(
            "Hot One", 1, 101, "hot_one"
        ),
    )
    events = (
        _event(10, 9991, SemanticEventKind.CAST),
        _event(10, 9992, SemanticEventKind.HEAL),
        _event(20, 101, SemanticEventKind.CAST),
        _event(30, 7777, SemanticEventKind.CAST),
    )

    rows = _candidate_caster_rows(
        events,
        targets,
        alias_map={"Hot One": (101, 9991, 9992)},
    )

    assert [row["source_id"] for row in rows] == [10, 20]
    assert rows[0]["abilities"] == ("Hot One",)
    assert rows[0]["casts"] == 1
    assert rows[0]["heals"] == 1


def test_candidate_caster_rows_ignore_untracked_and_missing_sources():
    targets = (RotationHealerEsoLogsObservationTarget("Hot", 1, 101),)
    events = (
        _event(None, 101, SemanticEventKind.CAST),
        _event(5, 999, SemanticEventKind.CAST),
        _event(6, 101, object()),
    )

    assert _candidate_caster_rows(events, targets) == ()


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
    assert "--list-casters" in result.stdout
    assert "--report-code" in result.stdout
    assert "candidate" in result.stdout.casefold()
