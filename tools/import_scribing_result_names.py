from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE


_ROW_RE = re.compile(r"\[\s*\d+\s*\]\s*=\s*\"((?:\\.|[^\"])*)\"")
_EXPECTED_FIELDS = 13
_PROBE_GRIMOIRE = "Soul Burst"
_PROBE_FOCUS = "Damage Shield"
_PROBE_RESULT = "Warding Burst"


@dataclass(frozen=True)
class ExtractRow:
    crafted_ability_id: int
    grimoire_name: str
    focus_script_id: int
    focus_name: str
    signature_script_id: int
    signature_name: str
    affix_script_id: int
    affix_name: str
    representative_ability_id: int
    representative_name: str
    ability_id: int
    ability_name: str
    crafted_description: str


def _decode_lua_string(value: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            result.append(char)
            index += 1
            continue
        nxt = value[index + 1]
        replacements = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "\\": "\\",
            '"': '"',
        }
        if nxt in replacements:
            result.append(replacements[nxt])
            index += 2
            continue
        if nxt.isdigit():
            digits = []
            cursor = index + 1
            while cursor < len(value) and len(digits) < 3 and value[cursor].isdigit():
                digits.append(value[cursor])
                cursor += 1
            try:
                result.append(chr(int("".join(digits))))
                index = cursor
                continue
            except ValueError:
                pass
        result.append(nxt)
        index += 2
    return "".join(result)


def _extract_table_block(text: str, key: str) -> str:
    marker = f'["{key}"]'
    start = text.find(marker)
    if start < 0:
        raise ValueError(f"SavedVariables does not contain {marker}")
    brace = text.find("{", start)
    if brace < 0:
        raise ValueError(f"SavedVariables key {marker} has no table value")

    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace : index + 1]
    raise ValueError(f"SavedVariables key {marker} contains an unterminated table")


def _extract_scalar(text: str, key: str, default: str = "") -> str:
    pattern = re.compile(
        rf'\["{re.escape(key)}"\]\s*=\s*(?:"((?:\\.|[^\"])*)"|([^,\r\n}}]+))'
    )
    match = pattern.search(text)
    if not match:
        return default
    if match.group(1) is not None:
        return _decode_lua_string(match.group(1))
    return str(match.group(2) or "").strip()


def _as_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def load_rows(path: Path) -> tuple[list[ExtractRow], int, str, bool]:
    text = path.read_text(encoding="utf-8", errors="replace")
    block = _extract_table_block(text, "exportRows")
    api_version = _as_int(_extract_scalar(text, "apiVersion", "0"))
    game_version = _extract_scalar(text, "gameVersion", "")
    completed = _extract_scalar(text, "completed", "false").casefold() == "true"

    rows: list[ExtractRow] = []
    for match in _ROW_RE.finditer(block):
        decoded = _decode_lua_string(match.group(1))
        parts = decoded.split("|")
        if len(parts) != _EXPECTED_FIELDS:
            continue
        rows.append(
            ExtractRow(
                crafted_ability_id=_as_int(parts[0]),
                grimoire_name=parts[1].strip(),
                focus_script_id=_as_int(parts[2]),
                focus_name=parts[3].strip(),
                signature_script_id=_as_int(parts[4]),
                signature_name=parts[5].strip(),
                affix_script_id=_as_int(parts[6]),
                affix_name=parts[7].strip(),
                representative_ability_id=_as_int(parts[8]),
                representative_name=parts[9].strip(),
                ability_id=_as_int(parts[10]),
                ability_name=parts[11].strip(),
                crafted_description=parts[12].strip(),
            )
        )
    return rows, api_version, game_version, completed


def choose_name_method(rows: list[ExtractRow]) -> tuple[str, bool]:
    probe = next(
        (
            row
            for row in rows
            if row.grimoire_name == _PROBE_GRIMOIRE and row.focus_name == _PROBE_FOCUS
        ),
        None,
    )
    if probe is None:
        return "", False
    if probe.representative_name == _PROBE_RESULT:
        return "representative_name", True
    if probe.ability_name == _PROBE_RESULT:
        return "ability_name", True
    return "", False


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS scribing_result_skill_source (
            source_key TEXT PRIMARY KEY,
            api_version INTEGER NOT NULL DEFAULT 0,
            game_version TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '',
            probe_verified INTEGER NOT NULL DEFAULT 0,
            name_method TEXT NOT NULL DEFAULT '',
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scribing_result_skill (
            crafted_ability_id INTEGER NOT NULL,
            grimoire_name TEXT NOT NULL,
            focus_script_id INTEGER NOT NULL,
            focus_name TEXT NOT NULL,
            signature_script_id INTEGER NOT NULL DEFAULT 0,
            signature_name TEXT NOT NULL DEFAULT '',
            affix_script_id INTEGER NOT NULL DEFAULT 0,
            affix_name TEXT NOT NULL DEFAULT '',
            representative_ability_id INTEGER NOT NULL DEFAULT 0,
            representative_name TEXT NOT NULL DEFAULT '',
            ability_id INTEGER NOT NULL DEFAULT 0,
            ability_name TEXT NOT NULL DEFAULT '',
            result_name TEXT NOT NULL DEFAULT '',
            crafted_description TEXT NOT NULL DEFAULT '',
            source_key TEXT NOT NULL,
            PRIMARY KEY (crafted_ability_id, focus_script_id),
            FOREIGN KEY (source_key) REFERENCES scribing_result_skill_source(source_key)
        );

        CREATE INDEX IF NOT EXISTS idx_scribing_result_name_lookup
            ON scribing_result_skill(grimoire_name, focus_name);
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import BFFScribingExtractor SavedVariables into data/eso.db. "
            "Result names are only promoted when the known Soul Burst + Damage Shield "
            "probe resolves to Warding Burst."
        )
    )
    parser.add_argument("saved_variables", help="Path to BFFScribingExtractorSavedVariables.lua")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE), help=f"Target DB (default: {DEFAULT_DATABASE})")
    args = parser.parse_args()

    source_path = Path(args.saved_variables).expanduser().resolve()
    database = Path(args.database).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"SavedVariables file not found: {source_path}")
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    rows, api_version, game_version, completed = load_rows(source_path)
    if not rows:
        raise ValueError("No exportRows were found in the SavedVariables file")

    name_method, probe_verified = choose_name_method(rows)
    source_key = f"eso_client_api:{api_version or 'unknown'}"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO scribing_result_skill_source(
                source_key, api_version, game_version, source_file,
                probe_verified, name_method, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_key) DO UPDATE SET
                api_version = excluded.api_version,
                game_version = excluded.game_version,
                source_file = excluded.source_file,
                probe_verified = excluded.probe_verified,
                name_method = excluded.name_method,
                imported_at = CURRENT_TIMESTAMP
            """,
            (
                source_key,
                api_version,
                game_version,
                str(source_path),
                1 if probe_verified else 0,
                name_method,
            ),
        )

        for row in rows:
            result_name = ""
            if probe_verified:
                result_name = (
                    row.representative_name
                    if name_method == "representative_name"
                    else row.ability_name
                )
            connection.execute(
                """
                INSERT INTO scribing_result_skill(
                    crafted_ability_id, grimoire_name,
                    focus_script_id, focus_name,
                    signature_script_id, signature_name,
                    affix_script_id, affix_name,
                    representative_ability_id, representative_name,
                    ability_id, ability_name,
                    result_name, crafted_description, source_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(crafted_ability_id, focus_script_id) DO UPDATE SET
                    grimoire_name = excluded.grimoire_name,
                    focus_name = excluded.focus_name,
                    signature_script_id = excluded.signature_script_id,
                    signature_name = excluded.signature_name,
                    affix_script_id = excluded.affix_script_id,
                    affix_name = excluded.affix_name,
                    representative_ability_id = excluded.representative_ability_id,
                    representative_name = excluded.representative_name,
                    ability_id = excluded.ability_id,
                    ability_name = excluded.ability_name,
                    result_name = excluded.result_name,
                    crafted_description = excluded.crafted_description,
                    source_key = excluded.source_key
                """,
                (
                    row.crafted_ability_id,
                    row.grimoire_name,
                    row.focus_script_id,
                    row.focus_name,
                    row.signature_script_id,
                    row.signature_name,
                    row.affix_script_id,
                    row.affix_name,
                    row.representative_ability_id,
                    row.representative_name,
                    row.ability_id,
                    row.ability_name,
                    result_name,
                    row.crafted_description,
                    source_key,
                ),
            )
        connection.commit()

    promoted = sum(
        1
        for row in rows
        if probe_verified
        and (
            row.representative_name if name_method == "representative_name" else row.ability_name
        )
    )

    print("========================================")
    print(" ESO SCRIBING RESULT-NAME IMPORT")
    print("========================================")
    print(f"SavedVariables:       {source_path}")
    print(f"Completed scan:       {completed}")
    print(f"API version:          {api_version}")
    print(f"Game version:         {game_version or 'unresolved'}")
    print(f"Rows imported:        {len(rows):,}")
    print(f"Probe verified:       {probe_verified}")
    print(f"Name method:          {name_method or 'unverified'}")
    print(f"Result names promoted:{promoted:>8,}")

    probe = next(
        (
            row
            for row in rows
            if row.grimoire_name == _PROBE_GRIMOIRE and row.focus_name == _PROBE_FOCUS
        ),
        None,
    )
    if probe:
        print()
        print("Known probe: Soul Burst + Damage Shield")
        print(f"  representative: {probe.representative_name or '—'} ({probe.representative_ability_id})")
        print(f"  ability:         {probe.ability_name or '—'} ({probe.ability_id})")
        print(f"  expected:        {_PROBE_RESULT}")

    if not completed:
        print()
        print("WARNING: SavedVariables says the scan was not complete.")
        return 3
    if not probe_verified:
        print()
        print("No result names were promoted because the known probe did not verify the API path.")
        print("Raw client observations were still imported for diagnosis.")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
