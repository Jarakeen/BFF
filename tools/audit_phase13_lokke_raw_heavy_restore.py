from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import load_semantic_events_from_json


def _resource_rows(events, *, source_id: int):
    return tuple(
        event
        for event in events
        if event.event_kind == SemanticEventKind.RESOURCE_CHANGE
        and event.source_id == int(source_id)
        and event.resource_change is not None
        and float(event.resource_change) > 0.0
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect positive resource-change events for one raw ESO Logs actor directly from "
            "the Lokkestiiz research JSON export. Candidate evidence only."
        )
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("research/raw/lokkestiiz_corpus.json"),
        help="raw ESO Logs JSON export",
    )
    parser.add_argument("--fight-id", type=int, default=6)
    parser.add_argument("--source-id", type=int, default=7)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    if int(args.limit) <= 0:
        raise ValueError("--limit must be positive")
    if not Path(args.path).exists():
        raise FileNotFoundError(args.path)

    events = load_semantic_events_from_json(Path(args.path), int(args.fight_id))
    rows = _resource_rows(events, source_id=int(args.source_id))

    print("=" * 112)
    print(" PHASE 13 LOKKE RAW ESO LOGS RESOURCE-RESTORE AUDIT")
    print("=" * 112)
    print("Evidence status: CANDIDATE OBSERVATION ONLY")
    print(f"Raw file:          {args.path}")
    print(f"Fight id:          {int(args.fight_id)}")
    print(f"Source id:         {int(args.source_id)}")
    print(f"Positive restores: {len(rows)}")
    print()

    if not rows:
        print("No positive resource-change events matched this raw actor/fight.")
        print("This means the raw export itself lacks resource restores for that source/fight,")
        print("not merely that the SQLite import omitted them.")
        return 3

    grouped = defaultdict(list)
    for event in rows:
        grouped[(event.ability_name, event.ability_game_id, event.resource_change_type)].append(
            float(event.resource_change)
        )

    print("POSITIVE RESOURCE-CHANGE ABILITY ALIASES")
    print("----------------------------------------")
    ranked = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), str(item[0][0] or ""), item[0][1] or -1),
    )
    for (name, ability_id, resource_type), amounts in ranked[: int(args.limit)]:
        print(
            f"{len(amounts):5d} events | ability={name or '(unnamed)'} [{ability_id}] | "
            f"resource_type={resource_type} | restore_range={min(amounts):g}..{max(amounts):g}"
        )

    print()
    print("MOST COMMON OBSERVED RESTORE AMOUNTS")
    print("------------------------------------")
    counts = Counter(float(event.resource_change) for event in rows)
    for amount, count in counts.most_common(int(args.limit)):
        print(f"{amount:10g} | {count:5d} events")

    print()
    print("EVENT PROVENANCE")
    print("----------------")
    for event in rows[: int(args.limit)]:
        print(
            f"{float(event.resource_change):10g} | event={event.event_index} "
            f"time={event.timestamp:g} ability={event.ability_name or '(unnamed)'} "
            f"[{event.ability_game_id}] resource_type={event.resource_change_type} "
            f"waste={event.waste} max_resource={event.max_resource_amount}"
        )

    print()
    print("BOUNDARY")
    print("--------")
    print("- Source id 7 is scoped to this reviewed Lokke raw log only.")
    print("- Numeric ability ids and resource type values remain raw ESO Logs evidence.")
    print("- Repeated amounts are candidate evidence, not automatic canonical constants.")
    print("- This tool reads raw JSON only and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
