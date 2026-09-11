from __future__ import annotations

import argparse
from collections import Counter
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


_RESOURCE_POOL_FIELDS = (
    ("magicka", "maxMagicka"),
    ("stamina", "maxStamina"),
    ("ultimate", "maxUltimate"),
    ("werewolf", "maxWerewolf"),
)


def _reported_post_event_pool_state(event):
    """Resolve the post-event pool from raw sourceResources without mapping enum ids.

    The raw event exposes maxResourceAmount plus a post-event sourceResources snapshot.
    Match the reported maximum to the corresponding pool's max field rather than
    assuming a hard-coded resourceChangeType enum mapping.
    """

    raw = event.raw_event if isinstance(event.raw_event, dict) else {}
    source_resources = raw.get("sourceResources")
    if not isinstance(source_resources, dict):
        return None

    max_amount = event.max_resource_amount
    if max_amount is None:
        max_amount = raw.get("maxResourceAmount")
    try:
        max_amount = float(max_amount)
    except (TypeError, ValueError):
        return None

    matches = []
    for current_key, max_key in _RESOURCE_POOL_FIELDS:
        current = source_resources.get(current_key)
        candidate_max = source_resources.get(max_key)
        try:
            current_value = float(current)
            candidate_max_value = float(candidate_max)
        except (TypeError, ValueError):
            continue
        if abs(candidate_max_value - max_amount) <= 0.5:
            matches.append((current_key, current_value, candidate_max_value))

    if len(matches) != 1:
        return None

    resource_name, current_value, max_value = matches[0]
    return {
        "resource": resource_name,
        "current": current_value,
        "maximum": max_value,
        "at_cap": current_value >= max_value - 0.5,
    }


def _cap_status(event) -> str:
    state = _reported_post_event_pool_state(event)
    if state is None:
        return "unresolved"
    return "at_reported_cap" if state["at_cap"] else "below_reported_cap"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify weapon-specific staff-heavy restore observations by whether the raw "
            "post-event ESO Logs resource snapshot is at the reported pool cap. Read-only."
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
                        _reported_post_event_pool_state(restore),
                    )
                )

    grouped = Counter(
        (
            label,
            float(restore.resource_change),
            _cap_status(restore),
        )
        for _fight, label, _completion, _start, _track, restore, _delta, _name, _role, _state in rows
    )

    print("=" * 112)
    print(" PHASE 13 STAFF HEAVY RESTORE CAP-CLIPPING AUDIT")
    print("=" * 112)
    print("Evidence status: OBSERVATIONAL RAW ESO LOGS POST-EVENT RESOURCE STATE")
    print(f"Raw corpus:           {args.path}")
    print(f"Report filter:        {args.report_code or 'all reports'}")
    print(f"Weapon-specific rows: {len(rows)}")
    print()

    print("RESTORE AMOUNTS BY REPORTED POST-EVENT CAP STATE")
    print("------------------------------------------------")
    for (label, amount, status), count in sorted(grouped.items()):
        print(f"{count:4d} | {label:24} | restore={amount:g} | {status}")

    print()
    print("ROW PROVENANCE")
    print("--------------")
    for fight, label, completion, start, effective_track, restore, delta, name, role, state in rows[: args.limit]:
        duration = _completion_duration_ms(start, completion)
        duration_text = "unknown" if duration is None else f"{duration:g}ms"
        if state is None:
            state_text = "pool=unresolved"
        else:
            state_text = (
                f"pool={state['resource']} post={state['current']:g}/{state['maximum']:g} "
                f"at_cap={state['at_cap']}"
            )
        print(
            f"{name} ({role}) | {label} | report={fight.report_code} fight={fight.fight_id} "
            f"source={completion.source_id} cast_track={effective_track} duration={duration_text} "
            f"restore={float(restore.resource_change):g} restore_id={restore.ability_game_id} "
            f"+{delta:g}ms | {state_text}"
        )

    print()
    print("BOUNDARY")
    print("--------")
    print("- 'at_reported_cap' means the raw post-event sourceResources pool equals its reported maximum.")
    print("- This is evidence of an effective gain ending at cap; it does not reconstruct the hidden attempted restore.")
    print("- The audit matches pools by maxResourceAmount and raw max fields instead of hard-coding resourceChangeType enum meanings.")
    print("- Numeric ids remain observational ESO Logs aliases only.")
    print("- No canonical HA base value or Off Balance state is inferred here.")
    print("- This audit reads research JSON and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
