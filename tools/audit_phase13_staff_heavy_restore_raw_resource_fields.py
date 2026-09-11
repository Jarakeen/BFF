from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase13_staff_heavy_attack_restore_corpus import (
    _completed_staff_heavies,
    _completion_duration_ms,
    _following_restores,
    _is_weapon_restore_candidate,
    _iter_corpus,
)


def _resource_raw_fields(event) -> dict[str, object]:
    raw = event.raw_event if isinstance(event.raw_event, dict) else {}
    selected = {}
    for key, value in raw.items():
        folded = str(key).casefold()
        if any(token in folded for token in ("resource", "waste", "max")):
            selected[str(key)] = value
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect raw ESO Logs resource fields for weapon-specific completed staff-heavy "
            "restore observations. Read-only observational diagnostic."
        )
    )
    parser.add_argument("--path", type=Path, default=Path("research/raw/lokkestiiz_corpus.json"))
    parser.add_argument("--forward-ms", type=float, default=500.0)
    parser.add_argument("--completion-pair-ms", type=float, default=5000.0)
    parser.add_argument("--report-code", default=None)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    if not args.path.exists():
        raise FileNotFoundError(args.path)
    if args.forward_ms < 0:
        raise ValueError("--forward-ms cannot be negative")
    if args.completion_pair_ms <= 0:
        raise ValueError("--completion-pair-ms must be positive")
    if args.limit <= 0:
        raise ValueError("--limit must be positive")

    rows = []
    for fight, roster_by_id, events in _iter_corpus(args.path):
        if args.report_code and fight.report_code != args.report_code:
            continue
        for label, completion, start, effective_track in _completed_staff_heavies(
            events,
            max_pair_gap_ms=float(args.completion_pair_ms),
        ):
            if completion.source_id is None:
                continue
            actor = roster_by_id.get(int(completion.source_id))
            if actor is None:
                continue
            name, role = actor
            for restore, delta in _following_restores(
                events,
                source_id=int(completion.source_id),
                timestamp=float(completion.timestamp),
                forward_ms=float(args.forward_ms),
            ):
                if not _is_weapon_restore_candidate(label, restore):
                    continue
                rows.append(
                    (
                        fight,
                        label,
                        completion,
                        start,
                        effective_track,
                        restore,
                        delta,
                        name,
                        role,
                    )
                )

    print("=" * 112)
    print(" PHASE 13 STAFF HEAVY RAW RESOURCE-FIELD AUDIT")
    print("=" * 112)
    print("Evidence status: OBSERVATIONAL RAW ESO LOGS FIELDS ONLY")
    print(f"Raw corpus:            {args.path}")
    print(f"Report filter:         {args.report_code or 'all reports'}")
    print(f"Weapon-specific rows:  {len(rows)}")
    print()

    for fight, label, completion, start, effective_track, restore, delta, name, role in rows[: args.limit]:
        duration = _completion_duration_ms(start, completion)
        duration_text = "unknown" if duration is None else f"{duration:g}ms"
        raw_fields = _resource_raw_fields(restore)
        print(
            f"{name} ({role}) | {label} | report={fight.report_code} fight={fight.fight_id} "
            f"source={completion.source_id} cast_track={effective_track} duration={duration_text} "
            f"restore={restore.resource_change} other_resource_change={restore.other_resource_change} "
            f"resource_type={restore.resource_change_type} max_resource={restore.max_resource_amount} "
            f"waste={restore.waste} restore_id={restore.ability_game_id} +{delta:g}ms"
        )
        print("  raw_resource_fields=" + json.dumps(raw_fields, sort_keys=True, ensure_ascii=False))

    print()
    print("BOUNDARY")
    print("--------")
    print("- This diagnostic reuses the reviewed completed-heavy and weapon-restore alias filters.")
    print("- It does not infer clipping, attempted restore, current resource, or canonical base values.")
    print("- Raw numeric ids remain observational ESO Logs aliases only.")
    print("- This audit reads research JSON and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
