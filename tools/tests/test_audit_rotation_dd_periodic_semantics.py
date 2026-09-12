from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.audit_rotation_dd_periodic_semantics as audit_tool
from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewEntry,
)


class _BuildService:
    def __init__(self, _path):
        pass

    def load(self):
        return SimpleNamespace(
            Members=(
                SimpleNamespace(Name="Magrat", BuildName="DF Healer", Role="Healer"),
                SimpleNamespace(Name="Rylonia", BuildName="Corpsebuster DD", Role="DD"),
            )
        )


def _build(name: str, build_name: str, role: str = "DD"):
    return SimpleNamespace(Name=name, BuildName=build_name, Role=role)


def test_non_dd_build_is_rejected_before_periodic_audit(monkeypatch, tmp_path, capsys) -> None:
    database_path = tmp_path / "eso.db"
    builds_path = tmp_path / "builds.json"
    database_path.touch()
    builds_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(audit_tool, "BuildService", _BuildService)

    class _ShouldNotRun:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("DD semantics audit must not run for a healer build")

    monkeypatch.setattr(
        audit_tool,
        "RotationDDPeriodicRuntimeSemanticsGapAuditService",
        _ShouldNotRun,
    )

    result = audit_tool.audit_saved_build(
        database_path=database_path,
        builds_path=builds_path,
        build_name="DF Healer",
    )

    assert result == 4
    output = capsys.readouterr().out
    assert "has role 'Healer'" in output
    assert "DD periodic damage runtime semantics only" in output
    assert "--list-dd" in output


def test_list_dd_filters_non_dd_builds_and_prints_copyable_command(
    monkeypatch, tmp_path, capsys
) -> None:
    builds_path = tmp_path / "builds.json"
    builds_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_tool, "BuildService", _BuildService)

    result = audit_tool.list_dd_builds(builds_path=builds_path)

    assert result == 0
    output = capsys.readouterr().out
    assert "Corpsebuster DD | Rylonia" in output
    assert '--build "Corpsebuster DD"' in output
    assert "DF Healer" not in output


def test_resolve_build_accepts_exact_build_name() -> None:
    build = _build("Rylonia", "Corpsebuster DD")

    assert audit_tool._resolve_build((build,), "Corpsebuster DD") is build


def test_resolve_build_accepts_unique_character_name() -> None:
    build = _build("Rylonia", "Corpsebuster DD")

    assert audit_tool._resolve_build((build,), "Rylonia") is build


def test_resolve_build_accepts_display_selector() -> None:
    build = _build("Rylonia", "Corpsebuster DD")

    assert audit_tool._resolve_build((build,), "Corpsebuster DD | Rylonia") is build


def test_resolve_build_rejects_ambiguous_character_name() -> None:
    builds = (
        _build("Rylonia", "Corpsebuster DD"),
        _build("Rylonia", "Parse DD"),
    )

    with pytest.raises(ValueError, match="matches multiple saved builds"):
        audit_tool._resolve_build(builds, "Rylonia")


def test_partial_review_formatter_separates_known_and_still_needed_fields() -> None:
    review = RotationDDPeriodicRuntimeSemanticsReviewEntry(
        skill_entity_id="skeletal_archer",
        coefficient_number=1,
        duration_seconds=20.0,
        reviewed_interval_seconds=2.0,
        successive_hit_multiplier=1.15,
        evidence=("reviewed tooltip cadence and growth",),
    )
    item = SimpleNamespace(partial_review=review)

    lines = audit_tool._format_partial_review(item)

    assert lines[0] == (
        "      known: duration=20s, interval=2s, successive_hit_multiplier=1.15"
    )
    assert lines[1] == (
        "      still needed: first_tick_offset_seconds, refresh_boundary, magnitude_policy"
    )
    assert lines[2] == "      review evidence: reviewed tooltip cadence and growth"
