from __future__ import annotations

"""Apply explicit human review decisions to a non-canonical strategy review packet."""

import argparse
import json
from pathlib import Path
import re

_VALID_STATUSES = {"accepted", "rejected"}
_CANONICAL_ID = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def apply_review_batch(*, packet_path: Path, batch_path: Path) -> tuple[int, int]:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    families = packet.get("candidate_hostile_families")
    decisions = batch.get("decisions")
    if not isinstance(families, list) or not isinstance(decisions, list):
        raise ValueError("packet and batch must contain candidate_hostile_families / decisions arrays")

    indexed: dict[int, dict] = {}
    for row in families:
        if not isinstance(row, dict) or not isinstance(row.get("ability_game_id"), int):
            raise ValueError("packet candidate family is missing integer ability_game_id")
        ability_id = int(row["ability_game_id"])
        if ability_id in indexed:
            raise ValueError(f"duplicate packet ability_game_id: {ability_id}")
        indexed[ability_id] = row

    changed = preserved = 0
    seen: set[int] = set()
    for raw in decisions:
        if not isinstance(raw, dict):
            raise ValueError("review decisions must be objects")
        ability_id = raw.get("ability_game_id")
        if not isinstance(ability_id, int):
            raise ValueError("review decision requires integer ability_game_id")
        if ability_id in seen:
            raise ValueError(f"duplicate review decision: {ability_id}")
        seen.add(ability_id)
        status = str(raw.get("status") or "").strip().casefold()
        rationale = str(raw.get("rationale") or "").strip()
        canonical_id_raw = raw.get("canonical_mechanic_id")
        canonical_id = None if canonical_id_raw is None else str(canonical_id_raw).strip()
        if status not in _VALID_STATUSES:
            raise ValueError(f"review decision {ability_id} must be accepted or rejected")
        if not rationale:
            raise ValueError(f"review decision {ability_id} requires rationale")
        if status == "accepted":
            if not canonical_id or not _CANONICAL_ID.fullmatch(canonical_id):
                raise ValueError(
                    f"accepted review decision {ability_id} requires lower_snake_case canonical_mechanic_id"
                )
        elif canonical_id:
            raise ValueError(f"rejected review decision {ability_id} cannot bind canonical_mechanic_id")

        target = indexed.get(ability_id)
        if target is None:
            raise ValueError(f"review decision ability id is not present in packet: {ability_id}")
        current = str(target.get("review_status") or "pending").strip().casefold()
        if current != "pending":
            preserved += 1
            continue
        target["review_status"] = status
        target["review_rationale"] = rationale
        target["canonical_mechanic_id"] = canonical_id if status == "accepted" else None
        changed += 1

    pending = sum(
        str(row.get("review_status") or "pending").strip().casefold() == "pending"
        for row in families
        if isinstance(row, dict)
    )
    state = packet.setdefault("review_state", {})
    if not isinstance(state, dict):
        raise ValueError("packet review_state must be an object")
    state["pending_human_review"] = bool(pending)
    state["canonical_strategy_changed"] = False
    state["canonical_mechanics_changed"] = False

    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed, preserved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply accepted/rejected human review decisions to a strategy research packet only."
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    args = parser.parse_args()
    try:
        changed, preserved = apply_review_batch(packet_path=args.packet, batch_path=args.batch)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"RESULT: BLOCKED\n{exc}")
        return 1
    print("PHASE 13 ENCOUNTER STRATEGY REVIEW APPLY")
    print(f"PACKET: {args.packet}")
    print(f"BATCH: {args.batch}")
    print(f"ROWS_CHANGED: {changed}")
    print(f"EXISTING_PRESERVED: {preserved}")
    print("CANONICAL_MECHANICS_CHANGED: 0")
    print("CANONICAL_STRATEGY_CHANGED: 0")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
