from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_encounter_store import UespEncounterStore
from services.uesp.uesp_parser import UespParser

CACHE = REPO_ROOT / "data" / "uesp" / ".cache"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Oaxiltso into a disposable copy of eso.db and verify the encounter rows."
    )
    parser.add_argument("database", type=Path, help="Path to the real eso.db")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "data" / "eso_oaxiltso_test.db",
        help="Disposable database copy to create",
    )
    args = parser.parse_args()

    source_db = args.database.resolve()
    test_db = args.output.resolve()

    if not source_db.exists():
        raise SystemExit(f"Database not found: {source_db}")

    if source_db == test_db:
        raise SystemExit("Refusing to use the real database as the test output.")

    test_db.parent.mkdir(parents=True, exist_ok=True)
    if test_db.exists():
        test_db.unlink()
    shutil.copy2(source_db, test_db)

    client = UespClient(CACHE)
    page = client.get_page("Online:Oaxiltso")
    boss = UespParser().parse_boss(
        page,
        content_id="rockgrove",
        content_name="Rockgrove",
    )

    connection = sqlite3.connect(test_db)
    try:
        store = UespEncounterStore(connection)
        store.save_boss(boss)

        encounter = connection.execute(
            "SELECT id, content_id, name, species, reaction, source_revision_id "
            "FROM encounter WHERE id = ?",
            (boss.id,),
        ).fetchone()
        health = connection.execute(
            "SELECT normal, veteran, hardmode FROM encounter_health WHERE encounter_id = ?",
            (boss.id,),
        ).fetchone()
        ability_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_ability WHERE encounter_id = ?",
            (boss.id,),
        ).fetchone()[0]
        dialogue_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_dialogue WHERE encounter_id = ?",
            (boss.id,),
        ).fetchone()[0]
        mechanic_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_mechanic WHERE encounter_id = ?",
            (boss.id,),
        ).fetchone()[0]

        assert encounter is not None, "encounter row was not written"
        assert health is not None, "health row was not written"
        assert ability_count == 8, f"expected 8 abilities, got {ability_count}"
        assert dialogue_count == 15, f"expected 15 dialogue lines, got {dialogue_count}"
        assert health[0] == "19,086,236"
        assert health[1] == "62,872,740"
        assert health[2] == "125,745,480"

        # Importing the same boss again must replace encounter-owned rows,
        # not duplicate them.
        store.save_boss(boss)
        ability_count_2 = connection.execute(
            "SELECT COUNT(*) FROM encounter_ability WHERE encounter_id = ?",
            (boss.id,),
        ).fetchone()[0]
        dialogue_count_2 = connection.execute(
            "SELECT COUNT(*) FROM encounter_dialogue WHERE encounter_id = ?",
            (boss.id,),
        ).fetchone()[0]
        assert ability_count_2 == 8, "second import duplicated abilities"
        assert dialogue_count_2 == 15, "second import duplicated dialogue"

        print("OAXILTSO DATABASE TEST PASSED")
        print(f"  test db:   {test_db}")
        print(f"  encounter: {encounter[0]}")
        print(f"  content:   {encounter[1]}")
        print(f"  abilities: {ability_count}")
        print(f"  mechanics: {mechanic_count}")
        print(f"  dialogue:  {dialogue_count}")
        print(f"  health:    {health[0]} / {health[1]} / {health[2]}")
        print(f"  source rev:{encounter[5]}")
        print("  idempotent: yes")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
