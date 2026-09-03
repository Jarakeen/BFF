from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List encounters whose Phase 10 requirements come from persisted reviewed "
            "canonical mechanic facts."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be positive")
    if not args.database.exists():
        print(f"RESULT: BLOCKED\nDatabase does not exist: {args.database}")
        return 1

    repository = EncounterRepository(
        args.data_root / "eso_info" / "bosses",
        args.data_root / "encounter_evidence",
        database_path=args.database,
    )
    service = EncounterService(repository)

    candidates = []
    for encounter_id in service.encounter_ids():
        encounter = service.get(encounter_id)
        canonical = tuple(
            mechanic
            for mechanic in encounter.mechanics
            if mechanic.mechanic_id.startswith(f"{encounter_id}:canonical:")
        )
        if not canonical:
            continue
        canonical_ids = {mechanic.mechanic_id for mechanic in canonical}
        requirements = tuple(
            row for row in service.requirements(encounter_id)
            if row.mechanic_id in canonical_ids
        )
        target_constraints = tuple(
            row for row in service.target_constraints(encounter_id)
            if row.mechanic_id in canonical_ids
        )
        candidates.append(
            (
                len(requirements),
                len(target_constraints),
                len(canonical),
                encounter_id,
                encounter.name,
                requirements,
                canonical,
            )
        )

    candidates.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))

    print("=" * 72)
    print(" PHASE 10 CANONICAL REVALIDATION CANDIDATES")
    print("=" * 72)
    print(f"Database:                         {args.database}")
    print(f"Encounters with canonical facts: {len(candidates)}")
    structured = sum(1 for row in candidates if row[0] or row[1])
    print(f"With structured Phase 10 input:  {structured}")
    print()

    for requirements_count, target_count, canonical_count, encounter_id, name, requirements, canonical in candidates[: args.limit]:
        print(
            f"{encounter_id} | {name} | canonical={canonical_count} "
            f"requirements={requirements_count} targets={target_count}"
        )
        if requirements:
            for requirement in requirements:
                print(
                    f"  REQUIREMENT {requirement.requirement_type}: "
                    f"{requirement.mechanic_name} "
                    f"[{requirement.interpretation_status}]"
                )
        else:
            names = ", ".join(mechanic.name for mechanic in canonical[:3])
            if len(canonical) > 3:
                names += f", ... (+{len(canonical) - 3})"
            print(f"  canonical mechanics: {names}")

    if not candidates:
        print("RESULT: BLOCKED")
        print("No persisted canonical mechanic facts reached the encounter repository.")
        return 1

    print()
    if structured:
        print("RESULT: PASS")
        print("Use the first candidate with requirements for the Phase 10 retrospective integration rerun.")
        return 0

    print("RESULT: BLOCKED")
    print("Canonical mechanics are visible, but none exposes structured Phase 10 requirements or target constraints.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
