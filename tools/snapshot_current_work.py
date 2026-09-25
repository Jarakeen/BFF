from __future__ import annotations

"""Create a read-safe SQLite checkpoint of current persisted FoundryDock work.

This deliberately does not mutate the canonical database. It is useful while the
desktop UI remains open and unsaved in-memory edits must not be disturbed.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_user_database_path
from services.user_safety_snapshot_service import UserSafetySnapshotService


def main() -> int:
    database = Path(get_user_database_path())
    snapshot = UserSafetySnapshotService(database_path=database).create(
        "emergency-current-work"
    )
    print(f"Canonical DB: {database}")
    if snapshot is None:
        print("ERROR: canonical user database does not exist; nothing was changed.")
        return 1
    print(f"Emergency persisted-state snapshot: {snapshot}")
    print("The live FoundryDock process was not modified or closed.")
    print("NOTE: this captures persisted SQLite state only; unsaved UI-only edits remain in the running app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
