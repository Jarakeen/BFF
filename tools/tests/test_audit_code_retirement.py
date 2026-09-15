from __future__ import annotations

from pathlib import Path

from tools.audit_code_retirement import inspect_candidate


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_runtime_import_keeps_candidate_live(tmp_path: Path) -> None:
    candidate = tmp_path / "services" / "candidate.py"
    _write(candidate, "VALUE = 1\n")
    _write(
        tmp_path / "ui" / "consumer.py",
        "from services.candidate import VALUE\n",
    )

    evidence = inspect_candidate(tmp_path, candidate)

    assert evidence.status == "LIVE_RUNTIME"
    assert [row.path for row in evidence.runtime_consumers] == ["ui/consumer.py"]


def test_tool_only_candidate_is_not_called_dead(tmp_path: Path) -> None:
    candidate = tmp_path / "services" / "repair.py"
    _write(candidate, "def repair():\n    return True\n")
    _write(
        tmp_path / "tools" / "repair_old_data.py",
        "from services.repair import repair\n",
    )

    evidence = inspect_candidate(tmp_path, candidate)

    assert evidence.status == "TOOLING_ONLY"
    assert [row.path for row in evidence.tool_consumers] == ["tools/repair_old_data.py"]


def test_test_only_candidate_remains_explicit(tmp_path: Path) -> None:
    candidate = tmp_path / "services" / "historical_math.py"
    _write(candidate, "VALUE = 1\n")
    _write(
        tmp_path / "services" / "tests" / "test_historical_math.py",
        "import services.historical_math\n",
    )

    evidence = inspect_candidate(tmp_path, candidate)

    assert evidence.status == "TEST_ONLY"
    assert [row.path for row in evidence.test_consumers] == [
        "services/tests/test_historical_math.py"
    ]


def test_no_static_imports_is_only_an_orphan_candidate(tmp_path: Path) -> None:
    candidate = tmp_path / "engine" / "unused.py"
    _write(candidate, "VALUE = 1\n")
    _write(tmp_path / "app.py", "print('hello')\n")

    evidence = inspect_candidate(tmp_path, candidate)

    assert evidence.status == "STATIC_ORPHAN_CANDIDATE"
    assert evidence.consumers == ()


def test_relative_imports_are_counted(tmp_path: Path) -> None:
    candidate = tmp_path / "services" / "helpers" / "candidate.py"
    _write(candidate, "VALUE = 1\n")
    _write(
        tmp_path / "services" / "helpers" / "consumer.py",
        "from .candidate import VALUE\n",
    )

    evidence = inspect_candidate(tmp_path, candidate)

    assert evidence.status == "LIVE_RUNTIME"
    assert [row.path for row in evidence.runtime_consumers] == [
        "services/helpers/consumer.py"
    ]
