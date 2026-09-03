from __future__ import annotations

"""Audit the persisted boss-guide read model across the encounter corpus."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.encounter_boss_guide import EncounterBossGuideService


EXPECTED_ENCOUNTERS = 490
EXPECTED_HEALTH_ROWS = 490
EXPECTED_ABILITIES = 2070
EXPECTED_PHASES = 4


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit persisted boss-guide projections across canonical encounters."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data" / "eso.db",
        help="Encounter SQLite database.",
    )
    args = parser.parse_args()

    service = EncounterBossGuideService(args.database)
    encounter_ids = service.encounter_ids()

    health_row_count = 0
    known_health_count = 0
    ability_count = 0
    phase_count = 0
    empty_ability_encounters: list[str] = []

    for encounter_id in encounter_ids:
        guide = service.get(encounter_id)
        if guide.health_record_present:
            health_row_count += 1
        if guide.health:
            known_health_count += 1
        ability_count += len(guide.abilities)
        phase_count += len(guide.phases)
        if not guide.abilities:
            empty_ability_encounters.append(encounter_id)

    expected = (
        len(encounter_ids) == EXPECTED_ENCOUNTERS
        and health_row_count == EXPECTED_HEALTH_ROWS
        and ability_count == EXPECTED_ABILITIES
        and phase_count == EXPECTED_PHASES
    )

    print("PERSISTED ENCOUNTER BOSS-GUIDE AUDIT")
    print(f"Database: {args.database}")
    print()
    print(f"Encounters projected:          {len(encounter_ids)} / {EXPECTED_ENCOUNTERS}")
    print(f"Persisted health records:      {health_row_count} / {EXPECTED_HEALTH_ROWS}")
    print(f"Encounters with known health:  {known_health_count}")
    print(f"Named abilities projected:     {ability_count} / {EXPECTED_ABILITIES}")
    print(f"Explicit phases projected:     {phase_count} / {EXPECTED_PHASES}")
    print(f"Encounters with zero abilities:{len(empty_ability_encounters):>6}")

    hiath = service.get("hiath_the_battlemaster")
    print()
    print("HIATH SAMPLE")
    print(f"  Content:    {hiath.content_name}")
    print(f"  Encounter:  {hiath.name}")
    print(f"  Location:   {hiath.location}")
    print(f"  Health row: {'present' if hiath.health_record_present else 'missing'}")
    print(f"  Health:     {dict(hiath.health)}")
    print(f"  Abilities:  {len(hiath.abilities)}")
    print(f"  Phases:     {len(hiath.phases)}")
    for ability in hiath.abilities[:5]:
        interrupt = (
            "interruptible"
            if ability.interruptible is True
            else "not_interruptible"
            if ability.interruptible is False
            else "interrupt_unknown"
        )
        print(f"    - {ability.name} [{interrupt}]")

    print()
    if expected:
        print("RESULT: PASS")
        print("The boss-guide read model matches the persisted structural encounter inventory.")
        print(
            "Known health values are reported separately; blank persisted health rows remain explicit unresolved coverage."
        )
        return 0

    print("RESULT: BLOCKED")
    print("Boss-guide projection counts do not match the audited structural persistence baseline.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
