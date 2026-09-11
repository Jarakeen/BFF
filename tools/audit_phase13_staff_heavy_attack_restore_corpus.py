from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.esologs_event_interpreter import SemanticEventKind
from services.esologs_json_adapter import EsoLogsJsonEventInterpreter, EsoLogsJsonFight


STAFF_HEAVY_ALIASES = {
    15383: "flame_staff_heavy",
    18396: "shock_staff_heavy",
    16212: "restoration_staff_heavy",
    16261: "frost_staff_heavy",
}

# Reviewed observational resource-change aliases from the current raw Lokke corpus.
# These are log-side evidence handles only, not canonical BFF mechanic identities.
STAFF_HEAVY_RESTORE_ALIASES = {
    "restoration_staff_heavy": frozenset({32760}),
    "frost_staff_heavy": frozenset({60762}),
    "shock_staff_heavy": frozenset({60764}),
}

CHANNELLED_STAFF_HEAVIES = {
    "restoration_staff_heavy",
    "shock_staff_heavy",
}

CHARGE_RELEASE_STAFF_HEAVIES = {
    "flame_staff_heavy",
    "frost_staff_heavy",
}


def _normalize_player_details(player_details):
    if isinstance(player_details, dict):
        nested = player_details.get("data") or player_details
        if isinstance(nested, dict):
            nested = nested.get("playerDetails") or nested
        player_details = nested

    rows = []
    if isinstance(player_details, dict):
        for role_key, role_name in (("healers", "healer"), ("tanks", "tank"), ("dps", "dps")):
            actors = player_details.get(role_key) or []
            if isinstance(actors, dict):
                actors = list(actors.values())
            if not isinstance(actors, list):
                continue
            for actor in actors:
                if not isinstance(actor, dict):
                    continue
                actor_id = actor.get("id")
                if actor_id is None:
                    continue
                rows.append(
                    (
                        int(actor_id),
                        str(actor.get("name") or actor.get("displayName") or f"source {actor_id}"),
                        role_name,
                    )
                )
    return tuple(rows)


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
            single_payload = {
                "report_code": str(report_code),
                "fights": {str(fight_id): fight_row},
            }
            fight = EsoLogsJsonFight.from_payload(
                single_payload,
                fight_id=fight_id,
                report_code=str(report_code),
                source_name=str(path),
            )
            roster = _normalize_player_details(fight_row.get("player_details") or {})
            roster_by_id = {actor_id: (name, role) for actor_id, name, role in roster}
            events = tuple(EsoLogsJsonEventInterpreter(fight).iter_events())
            yield fight, roster_by_id, events


def _following_restores(events, *, source_id: int, timestamp: float, forward_ms: float):
    rows = []
    for event in events:
        if event.event_kind != SemanticEventKind.RESOURCE_CHANGE:
            continue
        if event.source_id != source_id:
            continue
        if event.target_id != source_id:
            continue
        delta = float(event.timestamp) - float(timestamp)
        if delta < 0.0 or delta > forward_ms:
            continue
        if event.resource_change is None or float(event.resource_change) <= 0.0:
            continue
        rows.append((event, delta))
    return tuple(rows)


def _heavy_event_shape_key(label: str, event):
    return (
        label,
        str(event.raw_event_type or "unknown"),
        event.tick,
        event.cast_track_id is not None,
    )


def _is_weapon_restore_candidate(label: str, restore) -> bool:
    aliases = STAFF_HEAVY_RESTORE_ALIASES.get(label)
    if not aliases or restore.ability_game_id is None:
        return False
    return int(restore.ability_game_id) in aliases


def _completion_duration_ms(start, completion) -> float | None:
    if start is None:
        return None
    duration = float(completion.timestamp) - float(start.timestamp)
    return duration if duration >= 0.0 else None


def _latest_pending_start(pending, key, completion_time: float, *, max_gap_ms: float):
    starts = pending.get(key) or []
    for index in range(len(starts) - 1, -1, -1):
        start = starts[index]
        gap = float(completion_time) - float(start.timestamp)
        if gap < 0.0:
            continue
        if gap <= max_gap_ms:
            starts.pop(index)
            return start
        if gap > max_gap_ms:
            break
    return None


def _completed_staff_heavies(events, *, max_pair_gap_ms: float = 5000.0):
    """Collapse raw heavy-attack rows into one observational completion per attack.

    Restoration/Shock use cast -> channel rows -> removedebuff in the reviewed
    corpus. Frost/Flame use begincast -> cast charge/release rows. Numeric
    aliases remain observational and are not promoted into canonical identity.
    """

    if max_pair_gap_ms <= 0:
        raise ValueError("max_pair_gap_ms must be positive")

    ordered = sorted(events, key=lambda event: (float(event.timestamp), int(event.event_index)))
    pending_channel_casts = defaultdict(list)
    pending_charge_starts = defaultdict(list)
    completions = []

    for event in ordered:
        label = STAFF_HEAVY_ALIASES.get(event.ability_game_id)
        if label is None or event.source_id is None:
            continue

        raw_type = str(event.raw_event_type or "").strip().lower()
        key = (int(event.source_id), label)

        if label in CHANNELLED_STAFF_HEAVIES:
            if raw_type == "cast":
                pending_channel_casts[key].append(event)
                continue
            if raw_type != "removedebuff":
                continue

            start = _latest_pending_start(
                pending_channel_casts,
                key,
                float(event.timestamp),
                max_gap_ms=max_pair_gap_ms,
            )
            if start is None:
                continue

            completions.append((label, event, start, start.cast_track_id))
            continue

        if label in CHARGE_RELEASE_STAFF_HEAVIES:
            if raw_type == "begincast":
                pending_charge_starts[key].append(event)
                continue
            if raw_type != "cast":
                continue

            start = _latest_pending_start(
                pending_charge_starts,
                key,
                float(event.timestamp),
                max_gap_ms=max_pair_gap_ms,
            )
            effective_track = (
                start.cast_track_id
                if start is not None and start.cast_track_id is not None
                else event.cast_track_id
            )
            completions.append((label, event, start, effective_track))

    return tuple(completions)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan raw ESO Logs Lokkestiiz corpus roster players for reviewed staff-heavy "
            "log aliases and report following positive self-resource changes. Observational only."
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

    observations = []
    completion_counts = Counter()
    heavy_event_shapes = Counter()
    cast_track_ids = defaultdict(set)
    raw_heavy_rows = 0

    for fight, roster_by_id, events in _iter_corpus(args.path):
        if args.report_code and fight.report_code != args.report_code:
            continue

        for action in events:
            label = STAFF_HEAVY_ALIASES.get(action.ability_game_id)
            if label is None or action.source_id is None:
                continue
            actor = roster_by_id.get(int(action.source_id))
            if actor is None:
                continue
            raw_heavy_rows += 1
            heavy_event_shapes[_heavy_event_shape_key(label, action)] += 1
            if action.cast_track_id is not None:
                cast_track_ids[label].add(
                    (fight.report_code, fight.fight_id, int(action.source_id), int(action.cast_track_id))
                )

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
            completion_counts[(
                label,
                fight.report_code,
                fight.fight_id,
                int(completion.source_id),
                name,
                role,
            )] += 1

            for restore, delta in _following_restores(
                events,
                source_id=int(completion.source_id),
                timestamp=float(completion.timestamp),
                forward_ms=float(args.forward_ms),
            ):
                observations.append(
                    (fight, completion, start, effective_track, restore, delta, name, role, label)
                )

    weapon_restore_observations = tuple(
        row for row in observations if _is_weapon_restore_candidate(row[-1], row[4])
    )

    print("=" * 112)
    print(" PHASE 13 STAFF HEAVY-ATTACK SELF-RESTORE CORPUS AUDIT")
    print("=" * 112)
    print("Evidence status: OBSERVATIONAL LOG ALIASES ONLY")
    print(f"Raw corpus:              {args.path}")
    print(f"Report filter:           {args.report_code or 'all reports'}")
    print(f"Restore window:          {args.forward_ms:g} ms")
    print(f"Completion pair window:  {args.completion_pair_ms:g} ms")
    print(f"Roster actors with HA:   {len({row[1:6] for row in completion_counts})}")
    print(f"Raw staff-heavy rows:    {raw_heavy_rows}")
    print(f"Completed staff heavies: {sum(completion_counts.values())}")
    print(f"Following self restores: {len(observations)}")
    print(f"Weapon-specific restores:{len(weapon_restore_observations):5d}")

    print()
    print("STAFF HEAVY LOG SHAPES")
    print("----------------------")
    for (label, raw_type, tick, has_cast_track), count in heavy_event_shapes.most_common(args.limit):
        print(
            f"{count:5d} | {label:24} | raw_type={raw_type:12} | "
            f"tick={tick!s:5} | cast_track={'yes' if has_cast_track else 'no'}"
        )
    for label in sorted(STAFF_HEAVY_ALIASES.values()):
        if cast_track_ids.get(label):
            print(f"      | {label:24} | distinct_cast_tracks={len(cast_track_ids[label])}")

    print()
    print("COMPLETED STAFF HEAVIES BY PLAYER")
    print("---------------------------------")
    for (label, report_code, fight_id, source_id, name, role), count in completion_counts.most_common(args.limit):
        print(
            f"{count:4d} | {label:24} | {name} ({role}) | "
            f"report={report_code} fight={fight_id} source={source_id}"
        )

    by_restore = Counter(
        (
            label,
            float(restore.resource_change),
            restore.resource_change_type,
            restore.ability_game_id,
            restore.ability_name,
        )
        for _fight, _completion, _start, _track, restore, _delta, _name, _role, label in observations
    )
    print()
    print("SELF-RESTORE DISTRIBUTION BY COMPLETED STAFF HEAVY")
    print("--------------------------------------------------")
    for (label, amount, resource_type, restore_id, restore_name), count in by_restore.most_common(args.limit):
        print(
            f"{count:5d} | {label:24} | restore={amount:g} | "
            f"resource_type={resource_type} | restore_id={restore_id} | "
            f"restore_name={restore_name or 'unknown'}"
        )

    focused = defaultdict(list)
    for fight, completion, start, _track, restore, delta, name, role, label in weapon_restore_observations:
        duration = _completion_duration_ms(start, completion)
        focused[(label, float(restore.resource_change), restore.ability_game_id)].append(
            (duration, fight, completion, start, restore, delta, name, role)
        )

    print()
    print("WEAPON-SPECIFIC HEAVY RESTORE EVIDENCE")
    print("--------------------------------------")
    if not focused:
        print("none")
    else:
        for (label, amount, restore_id), rows in sorted(focused.items()):
            durations = [row[0] for row in rows if row[0] is not None]
            duration_text = "unknown"
            if durations:
                duration_text = (
                    f"min={min(durations):g}ms median={statistics.median(durations):g}ms "
                    f"max={max(durations):g}ms"
                )
            print(
                f"{len(rows):4d} | {label:24} | restore={amount:g} | restore_id={restore_id} | "
                f"duration[{duration_text}]"
            )

    print()
    print("WEAPON-SPECIFIC RESTORE PROVENANCE")
    print("----------------------------------")
    for fight, completion, start, effective_track, restore, delta, name, role, label in weapon_restore_observations[: args.limit]:
        duration = _completion_duration_ms(start, completion)
        duration_text = "unknown" if duration is None else f"{duration:g}ms"
        print(
            f"{name} ({role}) | {label} | report={fight.report_code} fight={fight.fight_id} "
            f"source={completion.source_id} cast_track={effective_track} duration={duration_text} "
            f"restore={float(restore.resource_change):g} restore_id={restore.ability_game_id} "
            f"+{delta:g}ms waste={restore.waste} max_resource={restore.max_resource_amount}"
        )

    per_actor = defaultdict(list)
    for fight, completion, _start, _track, restore, delta, name, role, label in observations:
        per_actor[(fight.report_code, fight.fight_id, int(completion.source_id), name, role, label)].append(
            (float(restore.resource_change), restore.resource_change_type, restore.ability_game_id, delta)
        )

    print()
    print("PER-PLAYER COMPLETED-HA SELF-RESTORE SUMMARY")
    print("--------------------------------------------")
    for key, rows in sorted(per_actor.items())[: args.limit]:
        report_code, fight_id, source_id, name, role, label = key
        common = Counter(value[0] for value in rows).most_common(5)
        common_text = ", ".join(f"{amount:g}x{count}" for amount, count in common)
        print(
            f"{name} ({role}) | {label} | report={report_code} fight={fight_id} "
            f"source={source_id} | restore_events={len(rows)} | common=[{common_text}]"
        )

    print()
    print("COMPLETION EVENT PROVENANCE")
    print("---------------------------")
    for fight, completion, start, effective_track, restore, delta, name, role, label in observations[: args.limit]:
        start_text = (
            f"start_event={start.event_index} start_type={start.raw_event_type}"
            if start is not None
            else "start_event=none start_type=none"
        )
        duration = _completion_duration_ms(start, completion)
        duration_text = "unknown" if duration is None else f"{duration:g}ms"
        print(
            f"{name} ({role}) | {label} | report={fight.report_code} fight={fight.fight_id} "
            f"source={completion.source_id} {start_text} cast_track={effective_track} "
            f"duration={duration_text} completion_event={completion.event_index} "
            f"completion_type={completion.raw_event_type} restore_event={restore.event_index} +{delta:g}ms "
            f"restore={float(restore.resource_change):g} resource_type={restore.resource_change_type} "
            f"restore_id={restore.ability_game_id} restore_name={restore.ability_name or 'unknown'} "
            f"waste={restore.waste} max_resource={restore.max_resource_amount}"
        )

    print()
    print("BOUNDARY")
    print("--------")
    print("- Staff-heavy numeric ids are reviewed ESO Logs aliases, not canonical BFF skill identities.")
    print("- Weapon-specific restore ids are observational corpus aliases, not promoted mechanics constants.")
    print("- Only actors present in each fight's player_details roster are included.")
    print("- Restoration/Shock completion requires a recent paired cast then removedebuff channel end.")
    print("- Frost/Flame completion uses the release cast; begincast is charge-start provenance when present.")
    print("- Resource events must be self-targeted (source_id == target_id) to count as HA restore candidates.")
    print("- Positive self-resource events inside the time window remain observational until reviewed.")
    print("- This audit reads raw research JSON and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
