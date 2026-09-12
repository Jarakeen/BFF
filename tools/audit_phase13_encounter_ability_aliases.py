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


_RELEVANT_HOSTILE_EVENT_TYPES = frozenset(
    {
        "begincast",
        "cast",
        "completecast",
        "damage",
        "applydebuff",
        "applydebuffstack",
        "refreshdebuff",
        "refreshdebuffstack",
        "removedebuff",
        "removedebuffstack",
    }
)


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


def discover_hostile_signatures(
    *,
    path: Path,
) -> tuple[tuple[str, int | None, str, bool | None, int, int], ...]:
    """Rank hostile cast/damage/debuff signatures across the whole corpus.

    ``fight_count`` is retained separately from raw occurrence count so one noisy wipe
    cannot make an otherwise irrelevant alias look like encounter-wide evidence.
    Output is observational only and does not bind any numeric alias to a canonical
    mechanic identity.
    """

    if not path.exists():
        raise FileNotFoundError(path)

    counts: Counter[tuple[str, int | None, str, bool | None]] = Counter()
    fights_by_signature: dict[tuple[str, int | None, str, bool | None], set[tuple[str, int]]] = {}
    for fight, events in _iter_corpus(path):
        fight_key = (str(fight.report_code), int(fight.fight_id))
        for event in events:
            if event.source_is_friendly is not False:
                continue
            raw_type = str(event.raw_event_type or "").strip().casefold()
            if raw_type not in _RELEVANT_HOSTILE_EVENT_TYPES:
                continue
            name = str(event.ability_name or "").strip()
            if not name and event.ability_game_id is None:
                continue
            signature = (name or "(unnamed)", event.ability_game_id, raw_type, event.tick)
            counts[signature] += 1
            fights_by_signature.setdefault(signature, set()).add(fight_key)

    ranked = sorted(
        counts.items(),
        key=lambda item: (
            -len(fights_by_signature.get(item[0], set())),
            -item[1],
            str(item[0][0]).casefold(),
            -1 if item[0][1] is None else int(item[0][1]),
            str(item[0][2]),
        ),
    )
    return tuple(
        (name, ability_id, raw_type, tick, count, len(fights_by_signature.get(signature, set())))
        for signature, count in ranked
        for name, ability_id, raw_type, tick in (signature,)
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
        default=[],
        help="Case-insensitive substring to match in ability names. Repeat as needed.",
    )
    parser.add_argument(
        "--all-hostile",
        action="store_true",
        help=(
            "Rank all hostile cast/damage/debuff signatures across the corpus instead of "
            "filtering by ability-name query."
        ),
    )
    parser.add_argument(
        "--include-friendly",
        action="store_true",
        help="Include friendly-source events as well as hostile-source events in query mode.",
    )
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    if args.limit <= 0:
        raise ValueError("--limit must be positive")
    if args.all_hostile and args.include_friendly:
        raise ValueError("--include-friendly is not valid with --all-hostile")
    if not args.all_hostile and not tuple(str(value).strip() for value in args.query):
        raise ValueError("provide at least one --query or use --all-hostile")

    print("PHASE 13 ENCOUNTER ABILITY ALIAS DISCOVERY")
    print(f"CORPUS: {args.path}")

    if args.all_hostile:
        rows = discover_hostile_signatures(path=args.path)
        print("MODE: all hostile cast/damage/debuff signatures")
        print(f"MATCHING_SIGNATURES: {len(rows)}")
        for name, ability_id, raw_type, tick, count, fight_count in rows[: args.limit]:
            print(
                f"SIGNATURE: fights={fight_count} count={count} name={name!r} "
                f"ability_id={ability_id} event_type={raw_type or 'unknown'} tick={tick}"
            )
        if not rows:
            print("RESULT: no hostile observational signatures found")
            return 1
        print("RESULT: candidate signatures only; review before canonical mechanic binding")
        return 0

    rows = discover_aliases(
        path=args.path,
        query_terms=tuple(args.query),
        hostile_only=not args.include_friendly,
    )

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
