from __future__ import annotations

"""Discover observational ESO Logs ability aliases inside one raw encounter corpus."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_json_adapter import EsoLogsJsonEventInterpreter, EsoLogsJsonFight


def _iter_corpus(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise ValueError(f"{path}: expected payload['reports'] object")

    for report_code, report_row in reports.items():
        if not isinstance(report_row, dict):
            continue
        fights = report_row.get("fights")
        if not isinstance(fights, dict):
            continue
        for fight_key, fight_row in fights.items():
            if not isinstance(fight_row, dict):
                continue
            fight_id = int(fight_key)
            fight = EsoLogsJsonFight.from_payload(
                {
                    "report_code": str(report_code),
                    "fights": {str(fight_id): fight_row},
                },
                fight_id=fight_id,
                report_code=str(report_code),
                source_name=str(path),
            )
            yield fight, tuple(EsoLogsJsonEventInterpreter(fight).iter_events())


def discover_aliases(
    *,
    path: Path,
    query_terms: tuple[str, ...],
    hostile_only: bool = True,
) -> tuple[tuple[str, int | None, str, bool | None, int], ...]:
    terms = tuple(str(term).strip().casefold() for term in query_terms if str(term).strip())
    if not terms:
        raise ValueError("at least one non-empty query term is required")
    if not path.exists():
        raise FileNotFoundError(path)

    counts: Counter[tuple[str, int | None, str, bool | None]] = Counter()
    for _fight, events in _iter_corpus(path):
        for event in events:
            if hostile_only and event.source_is_friendly is not False:
                continue
            name = str(event.ability_name or "").strip()
            if not name:
                continue
            folded = name.casefold()
            if not any(term in folded for term in terms):
                continue
            counts[(name, event.ability_game_id, str(event.raw_event_type or ""), event.tick)] += 1

    return tuple(
        (name, ability_id, raw_type, tick, count)
        for (name, ability_id, raw_type, tick), count in counts.most_common()
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Discover hostile ESO Logs ability aliases in a raw encounter corpus. "
            "Observational only; discovered names/ids are not promoted to canonical identity."
        )
    )
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument(
        "--query",
        action="append",
        required=True,
        help="Case-insensitive substring to match in ability names. Repeat as needed.",
    )
    parser.add_argument(
        "--include-friendly",
        action="store_true",
        help="Include friendly-source events as well as hostile-source events.",
    )
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    if args.limit <= 0:
        raise ValueError("--limit must be positive")

    rows = discover_aliases(
        path=args.path,
        query_terms=tuple(args.query),
        hostile_only=not args.include_friendly,
    )

    print("PHASE 13 ENCOUNTER ABILITY ALIAS DISCOVERY")
    print(f"CORPUS: {args.path}")
    print(f"QUERY: {', '.join(args.query)}")
    print(f"HOSTILE_ONLY: {str(not args.include_friendly).lower()}")
    print(f"MATCHING_SIGNATURES: {len(rows)}")
    for name, ability_id, raw_type, tick, count in rows[: args.limit]:
        print(
            f"ALIAS: count={count} name={name!r} ability_id={ability_id} "
            f"event_type={raw_type or 'unknown'} tick={tick}"
        )
    if not rows:
        print("RESULT: no matching observational ability aliases found")
        return 1
    print("RESULT: candidate aliases only; review before use by encounter observation services")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
