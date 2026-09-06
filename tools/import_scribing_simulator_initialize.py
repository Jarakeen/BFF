from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from services.scribing_catalog import compatible_focus, grimoire_names


INITIALIZE_URL = "https://eso-hub.com/api/scribing-simulator/initialize"
SOURCE_KEY = "eso_hub:scribing_simulator_initialize"
PROBE_GRIMOIRE = "Soul Burst"
PROBE_FOCUS = "Damage Shield"
PROBE_RESULT = "Warding Burst"


@dataclass(frozen=True)
class ResultPair:
    skill_id: int
    grimoire_name: str
    focus_script_id: int
    focus_name: str
    result_name: str


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def fetch_payload(timeout: float) -> dict[str, Any]:
    request = Request(
        INITIALIZE_URL,
        headers={
            "User-Agent": "BlackFeatherFoundry/1.0 (+https://github.com/Jarakeen/BFF)",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://eso-hub.com/en/scribing-simulator",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ESO-Hub initialize endpoint returned a non-object payload")
    return payload


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Scribing simulator initialize payload must be a JSON object")
    return payload


def _variation_for_focus(skill: dict[str, Any], focus_script_id: int) -> dict[str, Any] | None:
    variations = skill.get("variations") or {}
    if not isinstance(variations, dict):
        return None
    variation = variations.get(str(focus_script_id))
    if variation is None:
        variation = variations.get(focus_script_id)
    return variation if isinstance(variation, dict) else None


def extract_result_pairs(payload: dict[str, Any]) -> list[ResultPair]:
    scripts = payload.get("scripts") or []
    skills = payload.get("skills") or []
    if not isinstance(scripts, list) or not isinstance(skills, list):
        raise ValueError("Initialize payload must contain scripts[] and skills[]")

    script_by_id: dict[int, dict[str, Any]] = {}
    for row in scripts:
        if not isinstance(row, dict):
            continue
        script_id = _as_int(row.get("id"))
        if script_id > 0:
            script_by_id[script_id] = row

    pairs: list[ResultPair] = []
    seen: dict[tuple[str, str], str] = {}
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        skill_id = _as_int(skill.get("id"))
        grimoire_name = str(skill.get("name") or "").strip()
        script_ids = skill.get("scripts") or []
        if skill_id <= 0 or not grimoire_name or not isinstance(script_ids, list):
            continue

        for raw_script_id in script_ids:
            script_id = _as_int(raw_script_id)
            script = script_by_id.get(script_id)
            if not script or _as_int(script.get("type")) != 1:
                continue
            focus_name = str(script.get("name") or "").strip()
            if not focus_name:
                continue

            variation = _variation_for_focus(skill, script_id)
            result_name = str((variation or {}).get("name") or grimoire_name).strip()
            pair = (grimoire_name, focus_name)
            existing = seen.get(pair)
            if existing is not None and existing != result_name:
                raise ValueError(
                    f"Conflicting result names for {grimoire_name} + {focus_name}: "
                    f"{existing!r} vs {result_name!r}"
                )
            seen[pair] = result_name
            pairs.append(
                ResultPair(
                    skill_id=skill_id,
                    grimoire_name=grimoire_name,
                    focus_script_id=script_id,
                    focus_name=focus_name,
                    result_name=result_name,
                )
            )
    return pairs


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS scribing_result_name_reference_source (
            source_key TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_url TEXT NOT NULL,
            probe_verified INTEGER NOT NULL DEFAULT 0,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scribing_result_name_reference (
            source_key TEXT NOT NULL,
            grimoire_name TEXT NOT NULL,
            focus_name TEXT NOT NULL,
            result_name TEXT NOT NULL,
            combination_id INTEGER,
            page_url TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_key, grimoire_name, focus_name),
            FOREIGN KEY (source_key)
                REFERENCES scribing_result_name_reference_source(source_key)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scribing_simulator_script (
            source_key TEXT NOT NULL,
            script_id INTEGER NOT NULL,
            script_type INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT '',
            is_class_specific INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_key, script_id)
        );

        CREATE TABLE IF NOT EXISTS scribing_simulator_skill (
            source_key TEXT NOT NULL,
            skill_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT '',
            scripts_json TEXT NOT NULL DEFAULT '[]',
            forbidden_combinations_json TEXT NOT NULL DEFAULT '[]',
            raw_json TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_key, skill_id)
        );

        CREATE TABLE IF NOT EXISTS scribing_simulator_variation (
            source_key TEXT NOT NULL,
            skill_id INTEGER NOT NULL,
            focus_script_id INTEGER NOT NULL,
            result_name TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT '',
            cost TEXT NOT NULL DEFAULT '',
            cast_time TEXT NOT NULL DEFAULT '',
            channel_time TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL DEFAULT '',
            duration TEXT NOT NULL DEFAULT '',
            min_range TEXT NOT NULL DEFAULT '',
            max_range TEXT NOT NULL DEFAULT '',
            radius TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_key, skill_id, focus_script_id)
        );

        CREATE INDEX IF NOT EXISTS idx_scribing_result_name_reference_lookup
            ON scribing_result_name_reference(grimoire_name, focus_name);
        CREATE INDEX IF NOT EXISTS idx_scribing_simulator_script_type
            ON scribing_simulator_script(script_type, name COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_scribing_simulator_variation_lookup
            ON scribing_simulator_variation(skill_id, focus_script_id);
        """
    )


def import_payload(connection: sqlite3.Connection, payload: dict[str, Any]) -> tuple[int, int, int, int, bool]:
    scripts = payload.get("scripts") or []
    skills = payload.get("skills") or []
    if not isinstance(scripts, list) or not isinstance(skills, list):
        raise ValueError("Initialize payload must contain scripts[] and skills[]")

    pairs = extract_result_pairs(payload)
    pair_map = {(row.grimoire_name, row.focus_name): row for row in pairs}
    probe = pair_map.get((PROBE_GRIMOIRE, PROBE_FOCUS))
    probe_verified = bool(probe and probe.result_name == PROBE_RESULT)

    ensure_schema(connection)
    connection.execute(
        """
        INSERT INTO scribing_result_name_reference_source(
            source_key, source_kind, source_url, probe_verified, imported_at
        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(source_key) DO UPDATE SET
            source_kind = excluded.source_kind,
            source_url = excluded.source_url,
            probe_verified = excluded.probe_verified,
            imported_at = CURRENT_TIMESTAMP
        """,
        (SOURCE_KEY, "public_simulator_api", INITIALIZE_URL, 1 if probe_verified else 0),
    )

    for table in (
        "scribing_result_name_reference",
        "scribing_simulator_script",
        "scribing_simulator_skill",
        "scribing_simulator_variation",
    ):
        connection.execute(f"DELETE FROM {table} WHERE source_key = ?", (SOURCE_KEY,))

    script_count = 0
    for row in scripts:
        if not isinstance(row, dict):
            continue
        script_id = _as_int(row.get("id"))
        name = str(row.get("name") or "").strip()
        if script_id <= 0 or not name:
            continue
        connection.execute(
            """
            INSERT INTO scribing_simulator_script(
                source_key, script_id, script_type, name, icon,
                is_class_specific, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SOURCE_KEY,
                script_id,
                _as_int(row.get("type")),
                name,
                str(row.get("icon") or ""),
                1 if row.get("is_class_specific") else 0,
                json.dumps(row, ensure_ascii=False, sort_keys=True),
            ),
        )
        script_count += 1

    variation_count = 0
    skill_count = 0
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        skill_id = _as_int(skill.get("id"))
        name = str(skill.get("name") or "").strip()
        if skill_id <= 0 or not name:
            continue
        connection.execute(
            """
            INSERT INTO scribing_simulator_skill(
                source_key, skill_id, name, icon, scripts_json,
                forbidden_combinations_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SOURCE_KEY,
                skill_id,
                name,
                str(skill.get("icon") or ""),
                json.dumps(skill.get("scripts") or [], ensure_ascii=False),
                json.dumps(skill.get("scripts_forbidden_combinations") or [], ensure_ascii=False),
                json.dumps(skill, ensure_ascii=False, sort_keys=True),
            ),
        )
        skill_count += 1

        variations = skill.get("variations") or {}
        if isinstance(variations, dict):
            for raw_focus_id, variation in variations.items():
                if not isinstance(variation, dict):
                    continue
                focus_id = _as_int(raw_focus_id)
                result_name = str(variation.get("name") or "").strip()
                if focus_id <= 0 or not result_name:
                    continue
                connection.execute(
                    """
                    INSERT INTO scribing_simulator_variation(
                        source_key, skill_id, focus_script_id, result_name,
                        icon, cost, cast_time, channel_time, target, duration,
                        min_range, max_range, radius, description, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        SOURCE_KEY,
                        skill_id,
                        focus_id,
                        result_name,
                        str(variation.get("icon") or skill.get("icon") or ""),
                        str(variation.get("cost") or ""),
                        str(variation.get("cast_time") or ""),
                        str(variation.get("channel_time") or ""),
                        str(variation.get("target") or ""),
                        str(variation.get("duration") or ""),
                        str(variation.get("min_range") or ""),
                        str(variation.get("max_range") or ""),
                        str(variation.get("radius") or ""),
                        str(variation.get("description") or ""),
                        json.dumps(variation, ensure_ascii=False, sort_keys=True),
                    ),
                )
                variation_count += 1

    for row in pairs:
        connection.execute(
            """
            INSERT INTO scribing_result_name_reference(
                source_key, grimoire_name, focus_name, result_name,
                combination_id, page_url
            ) VALUES (?, ?, ?, ?, NULL, '')
            """,
            (
                SOURCE_KEY,
                row.grimoire_name,
                row.focus_name,
                row.result_name,
            ),
        )

    connection.commit()
    return script_count, skill_count, variation_count, len(pairs), probe_verified


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import the public ESO-Hub Scribing Simulator initialize payload. "
            "This captures scripts, skills, forbidden combinations, Focus variations, "
            "and explicit Grimoire + Focus -> result skill names."
        )
    )
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE),
        help=f"Target DB (default: {DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "--source-json",
        help="Optional saved initialize JSON; when omitted the public endpoint is fetched directly",
    )
    parser.add_argument("--save-json", help="Optional path to save the fetched initialize payload")
    parser.add_argument("--timeout", type=float, default=20.0, help="Network timeout in seconds")
    args = parser.parse_args()

    database = Path(args.database).expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    if args.source_json:
        source_path = Path(args.source_json).expanduser().resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Source JSON not found: {source_path}")
        payload = load_payload(source_path)
        source_label = str(source_path)
    else:
        payload = fetch_payload(args.timeout)
        source_label = INITIALIZE_URL
        if args.save_json:
            save_path = Path(args.save_json).expanduser().resolve()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )

    pairs = extract_result_pairs(payload)
    expected_pairs = {
        (grimoire, focus)
        for grimoire in grimoire_names()
        for focus in compatible_focus(grimoire)
    }
    observed_pairs = {(row.grimoire_name, row.focus_name) for row in pairs}
    missing = sorted(expected_pairs - observed_pairs, key=lambda row: (row[0].casefold(), row[1].casefold()))
    extra = sorted(observed_pairs - expected_pairs, key=lambda row: (row[0].casefold(), row[1].casefold()))

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        script_count, skill_count, variation_count, pair_count, probe_verified = import_payload(connection, payload)

    print("========================================")
    print(" ESO-HUB SCRIBING SIMULATOR IMPORT")
    print("========================================")
    print(f"Source:                 {source_label}")
    print(f"Scripts:                {script_count:,}")
    print(f"Skills / Grimoires:     {skill_count:,}")
    print(f"Focus variations:       {variation_count:,}")
    print(f"Result-name pairs:      {pair_count:,}")
    print(f"Known probe verified:   {probe_verified}")
    print(f"Static catalog missing: {len(missing):,}")
    print(f"Public-feed extras:     {len(extra):,}")

    if missing:
        print("\nPairs expected by BFF but absent from the public simulator feed:")
        for grimoire, focus in missing[:40]:
            print(f"  - {grimoire} + {focus}")
    if extra:
        print("\nPairs present in the public simulator feed but absent from BFF's static catalog:")
        for grimoire, focus in extra[:40]:
            print(f"  + {grimoire} + {focus}")

    if not probe_verified:
        print("\nThe Soul Burst + Damage Shield -> Warding Burst probe did not verify.")
        print("The rows were stored, but ScribingResultService will not promote this source.")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
