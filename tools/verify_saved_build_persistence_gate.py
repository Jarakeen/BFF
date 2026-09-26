from __future__ import annotations

"""Read-only acceptance gate for canonical Saved Build persistence."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_user_database_path
from services.user_build_catalog_pydantic_schema import validate_user_build_catalog_payload


def _raw_payload(path: Path) -> str:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        row = db.execute(
            "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
        ).fetchone()
    if row is None:
        raise RuntimeError("Canonical build_catalog row is missing.")
    return str(row[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect", type=int, default=None, help="Expected reusable Saved Build count.")
    args = parser.parse_args()

    database_path = get_user_database_path()
    before = _raw_payload(database_path)
    try:
        catalog = validate_user_build_catalog_payload(json.loads(before))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Canonical build_catalog failed strict validation: {exc}") from exc
    reusable = [
        row for row in catalog.get("builds", [])
        if isinstance(row, dict) and str(row.get("build_kind") or "saved").strip().casefold() != "comp"
    ]
    build_ids = [str(row.get("build_id") or "").strip() for row in reusable]
    if any(not value for value in build_ids):
        raise RuntimeError("Reusable Saved Build without BuildId.")
    if len(build_ids) != len(set(build_ids)):
        raise RuntimeError("Duplicate reusable Saved BuildId detected.")

    # BuildService is a projection of these canonical rows. Do not instantiate
    # application services in a read-only gate because their constructors may
    # perform migration/schema setup. Validate the durable rows directly.
    visible_ids = list(build_ids)
    after = _raw_payload(database_path)
    if after != before:
        raise RuntimeError("Read-only verification mutated canonical build_catalog payload.")
    if set(visible_ids) != set(build_ids):
        missing = sorted(set(build_ids) - set(visible_ids))
        extra = sorted(set(visible_ids) - set(build_ids))
        raise RuntimeError(f"BuildService projection mismatch; missing={missing}, extra={extra}.")
    if args.expect is not None and len(build_ids) != args.expect:
        raise RuntimeError(f"Expected {args.expect} reusable Saved Builds; found {len(build_ids)}.")

    digest = hashlib.sha256(before.encode("utf-8")).hexdigest()
    print(f"DB: {database_path}")
    print(f"Reusable Saved Builds: {len(build_ids)}")
    print(f"Canonical visible reusable Builds: {len(visible_ids)}")
    print(f"Catalog payload SHA256: {digest}")
    print("READ-ONLY GATE: PASS")
    for row in reusable:
        print(f"  {row.get('build_id')} | {row.get('name') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
