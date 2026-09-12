import json
import sqlite3

from services.esologs_report_provenance_service import EsoLogsReportProvenanceService


def _db(path, *, raw_json, request_json):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE log_report (report_code TEXT PRIMARY KEY, fetched_at TEXT, source_url TEXT, raw_json TEXT)"
        )
        db.execute(
            "CREATE TABLE log_import_manifest (id INTEGER PRIMARY KEY, report_code TEXT, request_json TEXT)"
        )
        db.execute(
            "INSERT INTO log_report VALUES (?,?,?,?)",
            ("REPORT", "2026-09-12T12:00:00+00:00", "https://www.esologs.com/reports/REPORT", json.dumps(raw_json)),
        )
        db.execute(
            "INSERT INTO log_import_manifest VALUES (1,?,?)",
            ("REPORT", json.dumps(request_json)),
        )
        db.commit()


def test_recovers_report_provenance_from_original_multi_report_source(tmp_path) -> None:
    source = tmp_path / "logs.json"
    source.write_text(
        json.dumps(
            {
                "reports": {
                    "REPORT": {
                        "startTime": 123456789,
                        "gameVersion": "U50",
                        "zone": {"id": 1, "name": "Trial"},
                        "fights": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "logs.db"
    _db(
        db_path,
        raw_json={"source_file": str(source), "fight": {"id": 1}},
        request_json={"source_file": str(source)},
    )

    report = EsoLogsReportProvenanceService(db_path).inspect()[0]

    assert report.report_code == "REPORT"
    assert report.source_file == str(source)
    assert report.source_file_exists is True
    assert report.source_report_keys == ("gameVersion", "startTime", "zone")
    assert ("gameVersion", "U50") in report.provenance_values
    assert ("startTime", "123456789") in report.provenance_values
    assert report.unresolved == ()


def test_missing_source_fails_closed_without_inventing_version(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    db_path = tmp_path / "logs.db"
    _db(
        db_path,
        raw_json={"source_file": str(missing), "fight": {"id": 1}},
        request_json={"source_file": str(missing)},
    )

    report = EsoLogsReportProvenanceService(db_path).inspect()[0]

    assert report.source_file_exists is False
    assert report.provenance_values == ()
    assert any("not present" in message for message in report.unresolved)
    assert any("no report-level date/version provenance" in message for message in report.unresolved)
