from __future__ import annotations

"""Small, portable backups for one FoundryDock Raid Plan."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from models.raid_plan import RaidPlan
from services.raid_plan_repository import RaidPlanRepository, RaidPlanRepositoryError


BACKUP_KIND = "foundrydock_raid_plan_backup"
BACKUP_SCHEMA_VERSION = 1


class RaidPlanBackupError(ValueError):
    """Raised when a Raid Plan backup file cannot be trusted."""


def export_raid_plan_backup(plan: RaidPlan, path: str | Path) -> Path:
    if not isinstance(plan, RaidPlan):
        raise TypeError("plan must be a RaidPlan")
    destination = Path(path)
    if destination.suffix.casefold() != ".json":
        destination = destination.with_suffix(".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": BACKUP_KIND,
        "schema_version": BACKUP_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "plan": asdict(plan),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    temp_name: str | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        os.replace(temp_name, destination)
    except OSError as exc:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise RaidPlanBackupError(f"could not write Raid Plan backup: {exc}") from exc
    return destination


def load_raid_plan_backup(path: str | Path) -> RaidPlan:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RaidPlanBackupError(f"could not read Raid Plan backup: {exc}") from exc

    if not isinstance(payload, dict):
        raise RaidPlanBackupError("Raid Plan backup root must be an object")

    # Current portable backups use the explicit FoundryDock backup envelope.
    # Early Phase 14 safety exports used the UI-draft-shaped envelope
    # {"payload": {"kind": "raid_plan", "plan": {...}}, "saved_at": ...}.
    # Accept that older *read-only file shape* so a safety file created during
    # the persistence incident remains recoverable. The decoded RaidPlan still
    # passes through the same canonical repository validation on restore.
    if payload.get("kind") == BACKUP_KIND:
        if payload.get("schema_version") != BACKUP_SCHEMA_VERSION:
            raise RaidPlanBackupError(
                f"unsupported Raid Plan backup schema: {payload.get('schema_version')!r}"
            )
        raw_plan = payload.get("plan")
    else:
        legacy_payload = payload.get("payload")
        if (
            isinstance(legacy_payload, dict)
            and legacy_payload.get("kind") == "raid_plan"
        ):
            raw_plan = legacy_payload.get("plan")
        else:
            raise RaidPlanBackupError("file is not a FoundryDock Raid Plan backup")

    if not isinstance(raw_plan, dict):
        raise RaidPlanBackupError("Raid Plan backup does not contain a plan")

    try:
        return RaidPlanRepository._decode_plan(raw_plan)
    except RaidPlanRepositoryError as exc:
        raise RaidPlanBackupError(f"invalid Raid Plan backup: {exc}") from exc


__all__ = [
    "BACKUP_KIND",
    "BACKUP_SCHEMA_VERSION",
    "RaidPlanBackupError",
    "export_raid_plan_backup",
    "load_raid_plan_backup",
]
