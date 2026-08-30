from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class CriticalEvidenceHit:
    ability_id: int
    name: str
    key_path: str
    value: str


@dataclass(frozen=True)
class CriticalEvidenceSummary:
    abilities_scanned: int
    raw_json_present: int
    invalid_json: int
    key_hits: tuple[CriticalEvidenceHit, ...]


def _walk_mapping(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            yield path, child
            yield from _walk_mapping(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]"
            yield from _walk_mapping(child, path)


def _display_value(value: Any, *, max_len: int = 160) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _key_mentions_critical(path: str) -> bool:
    return "crit" in path.casefold()


def load_critical_evidence(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> CriticalEvidenceSummary:
    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    sql = "SELECT ability_id, name, raw_json FROM ability ORDER BY ability_id"
    params: tuple[object, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (int(limit),)

    with sqlite3.connect(path) as db:
        rows = db.execute(sql, params).fetchall()

    raw_json_present = 0
    invalid_json = 0
    hits: list[CriticalEvidenceHit] = []

    for ability_id, name, raw_json in rows:
        if raw_json is None or not str(raw_json).strip():
            continue
        raw_json_present += 1
        try:
            payload = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError):
            invalid_json += 1
            continue

        for key_path, value in _walk_mapping(payload):
            if not _key_mentions_critical(key_path):
                continue
            hits.append(
                CriticalEvidenceHit(
                    ability_id=int(ability_id),
                    name=str(name or ""),
                    key_path=key_path,
                    value=_display_value(value),
                )
            )

    return CriticalEvidenceSummary(
        abilities_scanned=len(rows),
        raw_json_present=raw_json_present,
        invalid_json=invalid_json,
        key_hits=tuple(hits),
    )


def summarize_key_paths(
    hits: tuple[CriticalEvidenceHit, ...],
) -> Counter[tuple[str, str]]:
    return Counter((hit.key_path, hit.value) for hit in hits)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect imported ability.raw_json for explicit field names that may "
            "carry critical-hit eligibility. Read-only; this tool does not infer "
            "or write can_crit classifications."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    summary = load_critical_evidence(args.database, limit=args.limit)
    counts = summarize_key_paths(summary.key_hits)

    print("\n========================================")
    print(" PHASE 3 CRITICAL ELIGIBILITY EVIDENCE AUDIT")
    print("========================================")
    print(f"Database:             {args.database}")
    print(f"Abilities scanned:    {summary.abilities_scanned}")
    print(f"raw_json present:     {summary.raw_json_present}")
    print(f"Invalid raw_json:     {summary.invalid_json}")
    print(f"Critical-key hits:    {len(summary.key_hits)}")
    print()
    print("NOTE: only JSON KEY NAMES containing 'crit' are considered evidence candidates.")
    print("Tooltip/description prose is intentionally not treated as a crit-eligibility flag.")
    print("This audit is read-only and never writes can_crit.")

    if not counts:
        print("\nNo raw JSON key names containing 'crit' were found.")
        return 0

    print("\nKEY/VALUE DISTRIBUTION")
    for (key_path, value), count in counts.most_common(30):
        print(f"  {count:5}  {key_path} = {value}")

    print("\nREPRESENTATIVE HITS")
    for hit in summary.key_hits[: max(0, args.samples)]:
        print(
            f"  ability={hit.ability_id} name={hit.name} "
            f"{hit.key_path}={hit.value}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
