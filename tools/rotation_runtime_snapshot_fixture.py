from __future__ import annotations

import json
from pathlib import Path

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_target_type import SupportTargetType
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse, ExtremeRuntimeSnapshot


def load_rotation_runtime_snapshot_fixture(path: str | Path) -> ExtremeRuntimeSnapshot:
    """Load explicit authoritative runtime history for audit/runtime validation.

    This parser deliberately owns no runtime inference. Every history item must be
    stated by the fixture as an effect attempt, potion use, or external group-buff
    application. ConditionContext reconstruction is intentionally unsupported here;
    fixtures that need condition evidence should encode already-reviewed attempts
    through a richer production source instead of inventing condition state in an
    audit helper.
    """

    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime snapshot fixture root must be an object")

    raw_history = payload.get("runtime_history", ())
    if not isinstance(raw_history, list):
        raise ValueError("runtime snapshot fixture runtime_history must be a list")

    history = []
    for index, item in enumerate(raw_history):
        if not isinstance(item, dict):
            raise ValueError(
                f"runtime snapshot history item {index} must be an object"
            )
        kind = str(item.get("kind") or "").strip().casefold()
        if kind == "effect_attempt":
            if item.get("condition_context") is not None:
                raise ValueError(
                    "runtime snapshot fixture does not reconstruct condition_context"
                )
            event = RuntimeEvent(
                time_seconds=float(item["time_seconds"]),
                trigger=str(item["trigger"]),
                source=str(item["source"]),
                target=(
                    None
                    if item.get("target") is None
                    else str(item.get("target"))
                ),
                sequence=int(item.get("sequence", 0)),
            )
            chance_roll = item.get("chance_roll")
            history.append(
                RuntimeEffectEventAttempt(
                    event=event,
                    chance_roll=(
                        None if chance_roll is None else float(chance_roll)
                    ),
                )
            )
            continue

        if kind == "potion_use":
            history.append(
                ExtremeRuntimePotionUse(
                    time_seconds=float(item["time_seconds"]),
                    sequence=int(item.get("sequence", 0)),
                )
            )
            continue

        if kind == "external_group_buff":
            history.append(
                ExternalGroupBuffApplication(
                    source_actor_id=str(item["source_actor_id"]),
                    recipient_actor_id=str(item["recipient_actor_id"]),
                    buff_name=str(item["buff_name"]),
                    target_type=SupportTargetType(str(item["target_type"])),
                    applied_at_seconds=float(item["applied_at_seconds"]),
                    duration_seconds=float(item["duration_seconds"]),
                    source_evidence=str(item["source_evidence"]),
                    sequence=int(item.get("sequence", 0)),
                )
            )
            continue

        raise ValueError(
            f"runtime snapshot history item {index} has unsupported kind: {kind!r}"
        )

    return ExtremeRuntimeSnapshot(
        runtime_history=tuple(history),
        snapshot_time_seconds=float(payload.get("snapshot_time_seconds", 0.0)),
        recipient_actor_id=(
            None
            if payload.get("recipient_actor_id") is None
            else str(payload.get("recipient_actor_id"))
        ),
        group_member_ids=tuple(
            str(value)
            for value in payload.get("group_member_ids", ())
        ),
    )


__all__ = ["load_rotation_runtime_snapshot_fixture"]
