from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter, EsoLogsJsonFight


def _resource_rows(events, *, source_id: int):
    return tuple(
        event
        for event in events
        if event.event_kind == SemanticEventKind.RESOURCE_CHANGE
        and event.source_id == int(source_id)
        and event.resource_change is not None
        and float(event.resource_change) > 0.0
    )


def _load_corpus_fights(path: Path, *, fight_id: int):
    payload = json.loads(path.read_text(encoding="utf-8"))
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        raise ValueError(
            f"{path}: expected multi-report corpus payload['reports'] to be an object"
        )

    fights = []
    key = str(int(fight_id))
    for report_code, report in reports.items():
        if not isinstance(report, dict):
            continue
        report_fights = report.get("fights")
        if not isinstance(report_fights, dict):
            continue
        fight_payload = report_fights.get(key)
        if not isinstance(fight_payload, dict):
            continue
        wrapped = {
            "report_code": str(report_code),
            "fights": {key: fight_payload},
        }
        fights.append(
            EsoLogsJsonFight.from_payload(
                wrapped,
                fight_id=int(fight_id),
                report_code=str(report_code),
                source_name=str(path),
            )
        )
    return tuple(fights)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect positive resource-change events for one raw ESO Logs actor directly from "
            "the multi-report Lokkestiiz research corpus. Candidate evidence only."
        )
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("research/raw/lokkestiiz_corpus.json"),
        help="raw multi-report Lokkestiiz ESO Logs corpus",
    )
    parser.add_argument("--fight-id", type=int, default=6)
    parser.add_argument("--source-id", type=int, default=7)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    if int(args.limit) <= 0:
        raise ValueError("--limit must be positive")
    path = Path(args.path)
    if not path.exists():
        raise FileNotFoundError(path)

    fights = _load_corpus_fights(path, fight_id=int(args.fight_id))

    print("=" * 112)
    print(" PHASE 13 LOKKE RAW ESO LOGS RESOURCE-RESTORE AUDIT")
    print("=" * 112)
    print("Evidence status: CANDIDATE OBSERVATION ONLY")
    print(f"Raw file:          {args.path}")
    print(f"Fight id:          {int(args.fight_id)}")
    print(f"Source id:         {int(args.source_id)}")
    print(f"Matching reports:  {len(fights)}")

    if not fights:
        print()
        print("No report in the raw corpus contains that fight id.")
        print("Fight ids are report-local, so rerun with a reviewed fight id from the intended report.")
        return 3

    rows = []
    for fight in fights:
        interpreter = EsoLogsJsonEventInterpreter(fight)
        rows.extend(
            _resource_rows(
                tuple(interpreter.iter_events()),
                source_id=int(args.source_id),
            )
        )

    print(f"Positive restores: {len(rows)}")
    print()

    if not rows:
        print("No positive resource-change events matched this raw actor/fight across the matching reports.")
        print("This means the raw corpus itself lacks positive resource restores for source 7 at this fight id,")
        print("not merely that the SQLite import omitted them.")
        print()
        print("Matching report/fight rows:")
        for fight in fights:
            print(
                f"  report={fight.report_code} fight={fight.fight_id} "
                f"name={fight.name!r} events={fight.event_count}"
            )
        return 3

    grouped = defaultdict(list)
    for event in rows:
        grouped[
            (
                event.report_code,
                event.ability_name,
                event.ability_game_id,
                event.resource_change_type,
            )
        ].append(float(event.resource_change))

    print("POSITIVE RESOURCE-CHANGE ABILITY ALIASES")
    print("----------------------------------------")
    ranked = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], str(item[0][1] or ""), item[0][2] or -1),
    )
    for (report_code, name, ability_id, resource_type), amounts in ranked[: int(args.limit)]:
        print(
            f"{len(amounts):5d} events | report={report_code} | "
            f"ability={name or '(unnamed)'} [{ability_id}] | "
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
            f"{float(event.resource_change):10g} | report={event.report_code} "
            f"fight={event.fight_id} event={event.event_index} time={event.timestamp:g} "
            f"ability={event.ability_name or '(unnamed)'} [{event.ability_game_id}] "
            f"resource_type={event.resource_change_type} waste={event.waste} "
            f"max_resource={event.max_resource_amount}"
        )

    print()
    print("BOUNDARY")
    print("--------")
    print("- Source id 7 is scoped to the reviewed Lokke raw log/report where that identity was established.")
    print("- Fight ids are report-local; identical fight ids across reports remain separate provenance.")
    print("- Numeric ability ids and resource type values remain raw ESO Logs evidence.")
    print("- Repeated amounts are candidate evidence, not automatic canonical constants.")
    print("- This tool reads raw JSON only and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
