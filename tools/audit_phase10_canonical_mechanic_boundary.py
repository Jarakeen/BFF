from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.encounter_projection import load_encounter_definition
from services.encounter_repository import EncounterRepository


def _key(encounter_id: str, name: str) -> tuple[str, str]:
    return encounter_id, " ".join(str(name or "").strip().split()).casefold()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that raw inferred boss mechanics do not leak into downstream encounter "
            "consumption and that persisted canonical mechanics replace accepted reviews."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    args = parser.parse_args()

    bosses = args.data_root / "eso_info" / "bosses"
    evidence = args.data_root / "encounter_evidence"
    repository = EncounterRepository(bosses, evidence, database_path=args.database)

    raw_inferred: set[tuple[str, str]] = set()
    canonical: set[tuple[str, str]] = set()
    leaked: list[str] = []

    for encounter_id in repository.encounter_ids():
        raw = load_encounter_definition(
            repository._boss_paths[encounter_id],
            evidence_packet_path=repository._evidence_paths.get(encounter_id),
        )
        for mechanic in raw.mechanics:
            if str(mechanic.interpretation_status or "").strip().casefold() == "inferred":
                raw_inferred.add(_key(encounter_id, mechanic.name))

        downstream = repository.get(encounter_id)
        for mechanic in downstream.mechanics:
            identity = _key(encounter_id, mechanic.name)
            if mechanic.mechanic_id.startswith(f"{encounter_id}:canonical:"):
                canonical.add(identity)
            if (
                str(mechanic.interpretation_status or "").strip().casefold() == "inferred"
                and not mechanic.mechanic_id.startswith(f"{encounter_id}:canonical:")
            ):
                leaked.append(f"{encounter_id} :: {mechanic.name}")

    accepted_from_inferred = raw_inferred & canonical
    canonical_without_raw_inference = canonical - raw_inferred
    rejected_or_unpersisted = raw_inferred - canonical

    print("=" * 72)
    print(" PHASE 10 CANONICAL MECHANIC CONSUMPTION BOUNDARY")
    print("=" * 72)
    print(f"Database:                         {args.database}")
    print(f"Raw inferred source mechanics:   {len(raw_inferred)}")
    print(f"Canonical mechanic facts:        {len(canonical)}")
    print(f"Accepted inferred replacements:  {len(accepted_from_inferred)}")
    print(f"Rejected/unpersisted inferred:   {len(rejected_or_unpersisted)}")
    print(f"Canonical without raw inference: {len(canonical_without_raw_inference)}")
    print(f"Raw inferred downstream leaks:   {len(leaked)}")

    problems = []
    if canonical_without_raw_inference:
        problems.append(
            "canonical mechanic facts exist without a matching raw inferred source mechanic"
        )
    if leaked:
        problems.append("raw inferred mechanics remain visible downstream")

    # These are the reviewed-corpus invariants established by Phase 9. Keeping
    # the exact denominator here makes later source/review drift visible rather
    # than silently changing the Phase 10 consumption contract.
    expected = {
        "raw_inferred": 109,
        "accepted": 94,
        "rejected": 15,
    }
    if len(raw_inferred) != expected["raw_inferred"]:
        problems.append(
            f"raw inferred denominator changed: expected 109, found {len(raw_inferred)}"
        )
    if len(accepted_from_inferred) != expected["accepted"]:
        problems.append(
            f"accepted canonical replacements changed: expected 94, found {len(accepted_from_inferred)}"
        )
    if len(rejected_or_unpersisted) != expected["rejected"]:
        problems.append(
            f"rejected/unpersisted count changed: expected 15, found {len(rejected_or_unpersisted)}"
        )

    if problems:
        print("\nRESULT: BLOCKED")
        for problem in problems:
            print(f"  - {problem}")
        for row in leaked[:10]:
            print(f"  - LEAK: {row}")
        return 1

    print("\nRESULT: PASS")
    print("Phase 10 consumes accepted canonical mechanic truth and excludes rejected raw inference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
