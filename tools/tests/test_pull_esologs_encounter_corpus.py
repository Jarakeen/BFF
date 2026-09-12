from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.pull_esologs_encounter_corpus as tool


class _Client:
    pass


def test_pull_and_write_reuses_generic_corpus_pipeline(monkeypatch, tmp_path: Path) -> None:
    calls = {}
    client = _Client()

    def fake_client(settings_path: Path):
        calls["settings"] = settings_path
        return client

    def fake_pull_corpus(**kwargs):
        calls["pull"] = kwargs
        return {
            "schema_version": 1,
            "encounter": "reef guardian",
            "reports": {
                "6h4DjY8zNAxKMb2W": {
                    "matching_fight_count": 1,
                    "fights": {"7": {"event_count": 12, "events": []}},
                }
            },
        }

    monkeypatch.setattr(tool, "_client", fake_client)
    monkeypatch.setattr(tool, "pull_corpus", fake_pull_corpus)

    destination = tmp_path / "research" / "reef_guardian_corpus.json"
    result = tool.pull_and_write(
        encounter_name="Reef Guardian",
        report_codes=("https://www.esologs.com/reports/6h4DjY8zNAxKMb2W",),
        settings_path=tmp_path / "settings.json",
        destination=destination,
        event_limit=4321,
        include_resources=False,
    )

    assert calls["settings"] == tmp_path / "settings.json"
    assert calls["pull"] == {
        "client": client,
        "report_codes": ("https://www.esologs.com/reports/6h4DjY8zNAxKMb2W",),
        "encounter_name": "Reef Guardian",
        "include_resources": False,
        "event_limit": 4321,
    }
    assert json.loads(destination.read_text(encoding="utf-8")) == result


def test_pull_and_write_requires_explicit_encounter_and_report(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="encounter name cannot be empty"):
        tool.pull_and_write(
            encounter_name=" ",
            report_codes=("ABC",),
            settings_path=tmp_path / "settings.json",
            destination=tmp_path / "out.json",
        )

    with pytest.raises(ValueError, match="at least one ESO Logs report is required"):
        tool.pull_and_write(
            encounter_name="Reef Guardian",
            report_codes=(),
            settings_path=tmp_path / "settings.json",
            destination=tmp_path / "out.json",
        )
