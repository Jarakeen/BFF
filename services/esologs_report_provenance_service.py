from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any


_PROVENANCE_KEYS = (
    "startTime",
    "start_time",
    "endTime",
    "end_time",
    "gameVersion",
    "game_version",
    "clientVersion",
    "client_version",
    "version",
    "zone",
    "zoneID",
    "zone_id",
    "title",
    "owner",
)


@dataclass(frozen=True)
class EsoLogsReportProvenance:
    report_code: str
    fetched_at: str | None
    source_url: str | None
    source_file: str | None
    source_file_exists: bool
    stored_report_keys: tuple[str, ...]
    source_report_keys: tuple[str, ...]
    provenance_values: tuple[tuple[str, str], ...]
    unresolved: tuple[str, ...] = ()


class EsoLogsReportProvenanceService:
    """Recover report-era provenance from imported rows and original raw probe JSON.

    Read-only by design. The service never infers a game update from filenames, fight
    offsets, fetch time, or ability behavior. It reports only provenance actually
    present in the imported record or source JSON.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def inspect(self) -> tuple[EsoLogsReportProvenance, ...]:
        if not self.database_path.is_file():
            raise FileNotFoundError(self.database_path)

        uri = f"file:{self.database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            rows = db.execute(
                "SELECT report_code, fetched_at, source_url, raw_json "
                "FROM log_report ORDER BY report_code"
            ).fetchall()
            manifest_rows = db.execute(
                "SELECT report_code, request_json FROM log_import_manifest "
                "WHERE report_code IS NOT NULL ORDER BY id"
            ).fetchall()

        manifest_sources: dict[str, str] = {}
        for row in manifest_rows:
            payload = self._json_object(row["request_json"])
            source_file = payload.get("source_file")
            if isinstance(source_file, str) and source_file.strip():
                manifest_sources[str(row["report_code"])] = source_file.strip()

        results: list[EsoLogsReportProvenance] = []
        for row in rows:
            report_code = str(row["report_code"])
            stored = self._json_object(row["raw_json"])
            source_file = self._stored_source_file(stored) or manifest_sources.get(report_code)
            source_path = Path(source_file) if source_file else None
            source_payload = self._load_source(source_path)
            source_report = self._source_report(source_payload, report_code)

            values: dict[str, str] = {}
            for container in (stored.get("report"), source_report, stored):
                if not isinstance(container, dict):
                    continue
                for key in _PROVENANCE_KEYS:
                    if key in container and container[key] is not None and key not in values:
                        values[key] = self._display_value(container[key])

            unresolved: list[str] = []
            if not source_file:
                unresolved.append("original raw source file path is unavailable")
            elif source_path is not None and not source_path.is_file():
                unresolved.append("original raw source file is not present at the recorded path")
            if not values:
                unresolved.append("no report-level date/version provenance was found")

            results.append(
                EsoLogsReportProvenance(
                    report_code=report_code,
                    fetched_at=(str(row["fetched_at"]) if row["fetched_at"] is not None else None),
                    source_url=(str(row["source_url"]) if row["source_url"] is not None else None),
                    source_file=source_file,
                    source_file_exists=bool(source_path and source_path.is_file()),
                    stored_report_keys=tuple(sorted(stored.keys())),
                    source_report_keys=tuple(sorted(source_report.keys())),
                    provenance_values=tuple(values.items()),
                    unresolved=tuple(unresolved),
                )
            )
        return tuple(results)

    @staticmethod
    def _json_object(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str) or not value.strip():
            return {}
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _stored_source_file(stored: dict[str, Any]) -> str | None:
        value = stored.get("source_file")
        return value.strip() if isinstance(value, str) and value.strip() else None

    @classmethod
    def _load_source(cls, path: Path | None) -> dict[str, Any]:
        if path is None or not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _source_report(payload: dict[str, Any], report_code: str) -> dict[str, Any]:
        if not payload:
            return {}
        direct_code = str(payload.get("report_code") or "").strip()
        if direct_code == report_code:
            return {key: value for key, value in payload.items() if key != "fights"}
        reports = payload.get("reports")
        if isinstance(reports, dict):
            report = reports.get(report_code)
            if isinstance(report, dict):
                return {key: value for key, value in report.items() if key != "fights"}
        return {}

    @staticmethod
    def _display_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)


__all__ = ["EsoLogsReportProvenance", "EsoLogsReportProvenanceService"]
