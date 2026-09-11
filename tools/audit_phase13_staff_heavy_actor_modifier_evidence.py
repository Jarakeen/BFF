from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase13_staff_heavy_attack_restore_corpus import (
    _completed_staff_heavies,
    _following_restores,
    _iter_corpus,
)
from tools.audit_phase13_staff_heavy_restore_unclipped import _is_unclipped_weapon_restore


def _unwrap_player_details(player_details):
    value = player_details
    if isinstance(value, dict):
        value = value.get("data") or value
        if isinstance(value, dict):
            value = value.get("playerDetails") or value
    return value


def _raw_actor_by_id(player_details) -> dict[int, tuple[str, dict]]:
    value = _unwrap_player_details(player_details)
    actors: dict[int, tuple[str, dict]] = {}
    if not isinstance(value, dict):
        return actors

    for role_key, role_name in (("healers", "healer"), ("tanks", "tank"), ("dps", "dps")):
        rows = value.get(role_key) or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        if not isinstance(rows, list):
            continue
        for actor in rows:
            if not isinstance(actor, dict) or actor.get("id") is None:
                continue
            try:
                actor_id = int(actor["id"])
            except (TypeError, ValueError):
                continue
            actors[actor_id] = (role_name, actor)
    return actors


def _combatant_info(actor: dict) -> dict:
    info = actor.get("combatantInfo")
    return info if isinstance(info, dict) else actor


def _talent_names(actor: dict) -> tuple[str, ...]:
    info = _combatant_info(actor)
    talents = info.get("talents")
    if not isinstance(talents, list):
        talents = actor.get("talents") if isinstance(actor.get("talents"), list) else []

    names = []
    seen = set()
    for talent in talents:
        if isinstance(talent, dict):
            nested = talent.get("ability")
            name = talent.get("name") or talent.get("displayName")
            if not name and isinstance(nested, dict):
                name = nested.get("name")
        else:
            name = talent
        text = " ".join(str(name or "").split())
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            names.append(text)
    return tuple(names)


def _gear_rows(actor: dict) -> tuple[dict, ...]:
    info = _combatant_info(actor)
    gear = info.get("gear")
    if not isinstance(gear, list):
        gear = actor.get("gear") if isinstance(actor.get("gear"), list) else []
    return tuple(item for item in gear if isinstance(item, dict))


def _gear_set_names(actor: dict) -> tuple[str, ...]:
    names = []
    seen = set()
    for item in _gear_rows(actor):
        nested = item.get("set")
        name = item.get("setName") or item.get("set_name")
        if not name and isinstance(nested, dict):
            name = nested.get("name")
        elif not name and isinstance(nested, str):
            name = nested
        text = " ".join(str(name or "").split())
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            names.append(text)
    return tuple(names)


def _class_name(actor: dict) -> str:
    info = _combatant_info(actor)
    return " ".join(
        str(
            actor.get("type")
            or actor.get("class")
            or actor.get("className")
            or info.get("type")
            or info.get("class")
            or ""
        ).split()
    )


def _selected_combatant_scalars(actor: dict) -> dict[str, object]:
    info = _combatant_info(actor)
    selected = {}
    for key, value in info.items():
        if key in {"gear", "talents"}:
            continue
        if value is None or isinstance(value, (str, int, float, bool)):
            selected[str(key)] = value
    return selected


def _fight_rows(payload: dict):
    reports = payload.get("reports")
    if not isinstance(reports, dict):
        return
    for report_code, report_row in reports.items():
        if not isinstance(report_row, dict):
            continue
        fights = report_row.get("fights")
        if not isinstance(fights, dict):
            continue
        for fight_key, fight_row in fights.items():
            if isinstance(fight_row, dict):
                yield str(report_code), int(fight_key), fight_row


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect ESO Logs playerDetails/combatantInfo for actors with unclipped staff-heavy "
            "resource returns. Read-only observational modifier evidence."
        )
    )
    parser.add_argument("--path", type=Path, default=Path("research/raw/lokkestiiz_corpus.json"))
    parser.add_argument("--forward-ms", type=float, default=500.0)
    parser.add_argument("--completion-pair-ms", type=float, default=5000.0)
    parser.add_argument("--restore", type=float, default=4247.0)
    parser.add_argument("--label", default="restoration_staff_heavy")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    if not args.path.exists():
        raise FileNotFoundError(args.path)
    if args.forward_ms < 0:
        raise ValueError("--forward-ms cannot be negative")
    if args.completion_pair_ms <= 0:
        raise ValueError("--completion-pair-ms must be positive")
    if args.limit <= 0:
        raise ValueError("--limit must be positive")

    payload = json.loads(args.path.read_text(encoding="utf-8"))
    raw_actors = {}
    for report_code, fight_id, fight_row in _fight_rows(payload):
        raw_actors[(report_code, fight_id)] = _raw_actor_by_id(fight_row.get("player_details") or {})

    matched = defaultdict(list)
    for fight, _roster_by_id, events in _iter_corpus(args.path):
        for label, completion, _start, _track in _completed_staff_heavies(
            events,
            max_pair_gap_ms=float(args.completion_pair_ms),
        ):
            if label != args.label or completion.source_id is None:
                continue
            for restore, delta in _following_restores(
                events,
                source_id=int(completion.source_id),
                timestamp=float(completion.timestamp),
                forward_ms=float(args.forward_ms),
            ):
                if not _is_unclipped_weapon_restore(label, restore):
                    continue
                if abs(float(restore.resource_change) - float(args.restore)) > 0.5:
                    continue
                key = (fight.report_code, fight.fight_id, int(completion.source_id))
                matched[key].append((float(restore.resource_change), float(delta)))

    print("=" * 112)
    print(" PHASE 13 STAFF HEAVY ACTOR MODIFIER-EVIDENCE AUDIT")
    print("=" * 112)
    print("Evidence status: OBSERVATIONAL ESO LOGS PLAYERDETAILS / COMBATANTINFO ONLY")
    print(f"Raw corpus:       {args.path}")
    print(f"Heavy label:      {args.label}")
    print(f"Observed restore: {args.restore:g}")
    print(f"Matched actors:   {len(matched)}")
    print()

    for index, (key, observations) in enumerate(sorted(matched.items()), start=1):
        if index > args.limit:
            break
        report_code, fight_id, source_id = key
        role_actor = raw_actors.get((report_code, fight_id), {}).get(source_id)
        if role_actor is None:
            print(f"report={report_code} fight={fight_id} source={source_id} | player_details=missing")
            continue
        role, actor = role_actor
        name = str(actor.get("name") or actor.get("displayName") or f"source {source_id}")
        info = _combatant_info(actor)
        talent_names = _talent_names(actor)
        set_names = _gear_set_names(actor)
        gear = _gear_rows(actor)
        gear_keys = sorted({str(k) for row in gear for k in row.keys()})
        print(
            f"{name} ({role}) | class={_class_name(actor) or 'unknown'} | "
            f"report={report_code} fight={fight_id} source={source_id} | "
            f"unclipped_rows={len(observations)}"
        )
        print(f"  combatant_info_keys={sorted(str(k) for k in info.keys())}")
        print(f"  combatant_scalars={json.dumps(_selected_combatant_scalars(actor), sort_keys=True, ensure_ascii=False)}")
        print(f"  gear_item_keys={gear_keys}")
        print(f"  gear_sets={list(set_names)}")
        print(f"  talents={list(talent_names)}")
        if gear:
            print("  gear_rows=" + json.dumps(gear, sort_keys=True, ensure_ascii=False))

    print()
    print("BOUNDARY")
    print("--------")
    print("- This audit reports raw actor build evidence only; it does not infer canonical modifiers.")
    print("- Absence of a passive/talent in playerDetails is not proof that the player lacks it.")
    print("- Gear rows are printed so armor-weight or set evidence can be reviewed from actual exposed fields.")
    print("- No observed restore is promoted to verified_base_restore here.")
    print("- This audit reads research JSON and writes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
