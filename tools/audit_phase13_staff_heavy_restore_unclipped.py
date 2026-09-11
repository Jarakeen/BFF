from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import statistics
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
from tools.audit_phase13_staff_heavy_restore_cap_clipping import _cap_status


def _is_unclipped_weapon_restore(label: str, restore) -> bool:
    return _is_weapon_restore_candidate(label, restore) and _cap_status(restore) == "below_reported_cap"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report only below-cap weapon-specific completed staff-heavy restore observations. "
            "Read-only observational evidence; no canonical base-value inference."
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
                if not _is_unclipped_weapon_restore(label, restore):
                    continue
                rows.append((fight, label, completion, start, effective_track, restore, delta, name, role))

    grouped = Counter((label, float(restore.resource_change), restore.ability_game_id) for _fight, label, _completion, _start, _track, restore, _delta, _name, _role in rows)
    durations = defaultdict(list)
    actors = defaultdict(set)
    for fight, label, completion, start, _track, restore, _delta, name, role in rows:
        key = (label, float(restore.resource_change), restore.ability_game_id)
        duration = _completion_duration_ms(start, completion)
        if duration is not None:
            durations[key].append(duration)
        actors[key].add((fight.report_code, fight.fight_id, int(completion.source_id), name, role))

    print("=" * 112)
    print(" PHASE 13 STAFF HEAVY UNCLIPPED RESTORE AUDIT")
    print("=" * 112)
    print("Evidence status: OBSERVATIONAL BELOW-CAP WEAPON-SPECIFIC RETURNS ONLY")
    print(f"Raw corpus:            {args.path}")
    print(f"Report filter:         {args.report_code or 'all reports'}")
    print(f"Unclipped observations:{len(rows):5d}")
    print()

    print("UNCLIPPED RESTORE DISTRIBUTION")
    print("------------------------------")
    for key, count in sorted(grouped.items()):
        label, amount, restore_id = key
        observed_durations = durations.get(key, [])
        duration_text = "unknown"
        if observed_durations:
            duration_text = (
                f"min={min(observed_durations):g}ms "
                f"median={statistics.median(observed_durations):g}ms "
                f"max={max(observed_durations):g}ms"
            )
        print(
            f"{count:4d} | {label:24} | restore={amount:g} | restore_id={restore_id} | "
            f"actors={len(actors[key])} | duration[{duration_text}]"
        )

    print()
    print("PROVENANCE")
    print("----------")
    for fight, label, completion, start, effective_track, restore, delta, name, role in rows[: args.limit]:
        duration = _completion_duration_ms(start, completion)
        duration_text = "unknown" if duration is None else f"{duration:g}ms"
        print(
            f"{name} ({role}) | {label} | report={fight.report_code} fight={fight.fight_id} "
            f"source={completion.source_id} cast_track={effective_track} duration={duration_text} "
            f"restore={float(restore.resource_change):g} restore_id={restore.ability_game_id} +{delta:g}ms"
        )

    print()
    print("BOUNDARY")
    print("--------")
    print("- Rows at the reported post-event resource cap are excluded as cap-clipped effective gains.")
    print("- Numeric ids remain observational ESO Logs aliases only.")
    print("- Observed below-cap returns may still include passives, CP, gear, buffs, or target-state multipliers.")
    print("- This audit does not promote any observed return to verified_base_restore.")
    print("- This audit reads research JSON and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
