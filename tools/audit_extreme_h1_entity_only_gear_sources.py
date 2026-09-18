from __future__ import annotations

"""Audit source payload coverage for entity-only canonical gear sets."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from services.extreme_entity_only_gear_source_audit_service import (
    ExtremeEntityOnlyGearSourceAuditService,
)


def main() -> int:
    database = get_data_dir() / "eso.db"
    report = ExtremeEntityOnlyGearSourceAuditService(database).build()

    print("EXTREME H1 ENTITY-ONLY GEAR SOURCE AUDIT")
    print(f"database={database}")
    print(f"entity_only_count={report.entity_count}")
    print(f"with_source_count={report.with_source_count}")
    print(f"with_raw_payload_count={report.with_raw_payload_count}")
    print(f"without_source_count={report.without_source_count}")

    for row in report.rows:
        print()
        print(f"[{row.name}]")
        print(f"entity_id={row.entity_id}")
        print(f"source_count={row.source_count}")
        print(f"sources={row.sources}")
        print(f"source_entity_types={row.source_entity_types}")
        print(f"raw_json_count={row.raw_json_count}")
        print(f"raw_json_keys={row.raw_json_keys}")

    print()
    print(
        "NEXT_STEP=if raw payload coverage is substantial, build an additive "
        "arena/special-set normalizer from those source payloads; otherwise audit "
        "the missing upstream import source rather than inventing set bonuses"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
