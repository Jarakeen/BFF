from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_decisions import VALID_STATUSES


def apply_review_batch(manifest_path: Path, batch_path: Path) -> tuple[int, int]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    batch = json.loads(Path(batch_path).read_text(encoding="utf-8"))
    manifest_rows = manifest.get("decisions")
    batch_rows = batch.get("decisions")
    if not isinstance(manifest_rows, list) or not isinstance(batch_rows, list):
        raise ValueError("manifest and batch must each contain a decisions array")

    indexed: dict[tuple[str, str], dict] = {}
    for row in manifest_rows:
        if not isinstance(row, dict):
            raise ValueError("manifest decision rows must be objects")
        key = (str(row.get("encounter_id") or ""), str(row.get("mechanic_name") or ""))
        if key in indexed:
            raise ValueError(f"duplicate manifest decision key: {key!r}")
        indexed[key] = row

    changed = preserved = 0
    for raw in batch_rows:
        if not isinstance(raw, dict):
            raise ValueError("batch decision rows must be objects")
        encounter_id = str(raw.get("encounter_id") or "").strip()
        mechanic_name = str(raw.get("mechanic_name") or "").strip()
        status = str(raw.get("status") or "").strip().casefold()
        rationale = str(raw.get("rationale") or "").strip()
        key = (encounter_id, mechanic_name)
        if not encounter_id or not mechanic_name:
            raise ValueError("batch decision is missing encounter_id/mechanic_name")
        if status not in VALID_STATUSES or status == "pending":
            raise ValueError(f"batch decision must be accepted or rejected: {key!r}")
        if not rationale:
            raise ValueError(f"batch decision requires rationale: {key!r}")
        target = indexed.get(key)
        if target is None:
            raise ValueError(f"batch decision is not present in manifest: {key!r}")
        current = str(target.get("status") or "").strip().casefold()
        if current != "pending":
            preserved += 1
            continue
        target["status"] = status
        target["rationale"] = rationale
        changed += 1

    Path(manifest_path).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return changed, preserved


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a tracked inferred-mechanic review batch to the local review manifest.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "encounter_reviews" / "inferred_boss_mechanics.json",
    )
    parser.add_argument("--batch", type=Path, required=True)
    args = parser.parse_args()

    try:
        changed, preserved = apply_review_batch(args.manifest, args.batch)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"RESULT: BLOCKED\n{exc}")
        return 1

    print("=" * 72)
    print(" INFERRED MECHANIC REVIEW BATCH APPLY")
    print("=" * 72)
    print(f"Manifest:             {args.manifest}")
    print(f"Batch:                {args.batch}")
    print(f"Rows changed:         {changed}")
    print(f"Existing preserved:   {preserved}")
    print("Canonical encounter facts changed: 0")
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
