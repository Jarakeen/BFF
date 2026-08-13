from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser
from services.uesp.uesp_encounter_store import UespEncounterStore

CACHE = REPO_ROOT / "data" / "uesp" / ".cache"
PAGE_TITLE = "Online:Xalvakka"
EXPECTED_HEALTH = ("25,084,768", "53,558,256", "214,233,024")
EXPECTED_ABILITIES = 10
EXPECTED_DIALOGUE = 21
EXPECTED_PHASES = 6


def main() -> None:
    source_db = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "data" / "eso_backup.db"
    if not source_db.exists():
        raise SystemExit(f"Database not found: {source_db}")

    test_db = REPO_ROOT / "data" / "eso_xalvakka_test.db"
    if test_db.exists():
        test_db.unlink()
    shutil.copy2(source_db, test_db)

    client = UespClient(CACHE)
    page = client.get_page(PAGE_TITLE)
    parser = UespParser()
    boss = parser.parse_boss(page, content_id="rockgrove", content_name="Rockgrove")

    connection = sqlite3.connect(test_db)
    connection.row_factory = sqlite3.Row
    try:
        store = UespEncounterStore(connection)
        store.save_boss(boss)

        ability_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_ability WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0]
        mechanic_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_mechanic WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0]
        dialogue_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_dialogue WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0]
        phase_rows = connection.execute(
            "SELECT label, threshold, description FROM encounter_phase WHERE encounter_id = ? ORDER BY id", (boss.id,)
        ).fetchall()
        health_row = connection.execute(
            "SELECT normal, veteran, hardmode FROM encounter_health WHERE encounter_id = ?", (boss.id,)
        ).fetchone()

        health = tuple(health_row) if health_row is not None else None

        assert ability_count == EXPECTED_ABILITIES, f"Expected {EXPECTED_ABILITIES} abilities, got {ability_count}"
        assert dialogue_count == EXPECTED_DIALOGUE, f"Expected {EXPECTED_DIALOGUE} dialogue lines, got {dialogue_count}"
        assert len(phase_rows) == EXPECTED_PHASES, f"Expected {EXPECTED_PHASES} phases, got {len(phase_rows)}"
        assert health == EXPECTED_HEALTH, f"Xalvakka health mismatch: actual={health!r}, expected={EXPECTED_HEALTH!r}"
        assert mechanic_count > 0, "Expected inferred Xalvakka mechanics in the database"

        print("XALVAKKA DATABASE SNAPSHOT")
        print(f"  test db:   {test_db}")
        print(f"  encounter: {boss.id}")
        print(f"  content:   {boss.content_id}")
        print(f"  abilities: {ability_count}")
        print(f"  mechanics: {mechanic_count}")
        print(f"  phases:    {len(phase_rows)}")
        for index, row in enumerate(phase_rows, 1):
            print(f"    phase {index}: label={row['label']!r} threshold={row['threshold']!r}")
        print(f"  dialogue:  {dialogue_count}")
        print(f"  health:    {health[0]} / {health[1]} / {health[2]}")
        print(f"  source rev:{boss.source.revision_id if boss.source else None}")

        # Re-import to prove replacement/upsert behavior does not duplicate data.
        store.save_boss(boss)
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_ability WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0] == ability_count
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_mechanic WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0] == mechanic_count
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_phase WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0] == len(phase_rows)
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_dialogue WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0] == dialogue_count

        print("XALVAKKA DATABASE TEST PASSED")
        print("  idempotent: yes")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
