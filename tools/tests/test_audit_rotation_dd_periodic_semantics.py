from pathlib import Path
from types import SimpleNamespace

import tools.audit_rotation_dd_periodic_semantics as audit_tool


class _BuildService:
    def __init__(self, _path):
        pass

    def load(self):
        return SimpleNamespace(
            Members=(
                SimpleNamespace(Name="Magrat", BuildName="DF Healer", Role="Healer"),
                SimpleNamespace(Name="Parse Cat", BuildName="Parse DD", Role="DD"),
            )
        )


def test_non_dd_build_is_rejected_before_periodic_audit(monkeypatch, tmp_path, capsys) -> None:
    database_path = tmp_path / "eso.db"
    builds_path = tmp_path / "builds.json"
    database_path.touch()
    builds_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(audit_tool, "BuildService", _BuildService)
    monkeypatch.setattr(
        audit_tool,
        "_find_build",
        lambda members, requested: next(
            build for build in members if build.BuildName == requested
        ),
    )

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


def test_list_dd_filters_non_dd_builds(monkeypatch, tmp_path, capsys) -> None:
    builds_path = tmp_path / "builds.json"
    builds_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_tool, "BuildService", _BuildService)

    result = audit_tool.list_dd_builds(builds_path=builds_path)

    assert result == 0
    output = capsys.readouterr().out
    assert "Parse DD | Parse Cat" in output
    assert "DF Healer" not in output
