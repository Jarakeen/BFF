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
PAGE_TITLE = "Online:Flame-Herald Bahsei"

EXPECTED_CURATED = {
    "Bahsei's Salvo",
    "Death Touch",
    "Cursed Ground",
    "Sickle Strike",
    "Behemoth Spawn",
    "Specter Spawn",
}
EXPECTED_HEALTH = ("21,812,840", "65,201,356", "123,882,576")


def main() -> None:
    source_db = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "data" / "eso_backup.db"
    if not source_db.exists():
        raise SystemExit(f"Database not found: {source_db}")

    test_db = REPO_ROOT / "data" / "eso_bahsei_test.db"
    if test_db.exists():
        test_db.unlink()
    shutil.copy2(source_db, test_db)

    client = UespClient(CACHE)
    page = client.get_page(PAGE_TITLE)
    parser = UespParser()
    boss = parser.parse_boss(page, content_id="rockgrove", content_name="Rockgrove")

    connection = sqlite3.connect(test_db)
    try:
        store = UespEncounterStore(connection)
        store.save_boss(boss)

        mechanic_rows = connection.execute(
            "SELECT name, interpretation_status FROM encounter_mechanic WHERE encounter_id = ? ORDER BY name",
            (boss.id,),
        ).fetchall()
        strategy_rows = connection.execute(
            "SELECT strategy FROM encounter_strategy WHERE encounter_id = ?",
            (boss.id,),
        ).fetchall()
        ability_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_ability WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0]
        dialogue_count = connection.execute(
            "SELECT COUNT(*) FROM encounter_dialogue WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0]
        health_row = connection.execute(
            "SELECT normal, veteran, hardmode FROM encounter_health WHERE encounter_id = ?", (boss.id,)
        ).fetchone()
        health = tuple(health_row) if health_row is not None else None

        names = {row[0] for row in mechanic_rows}
        statuses = {row[0]: row[1] for row in mechanic_rows}
        missing = EXPECTED_CURATED - names
        assert not missing, f"Missing curated Bahsei mechanics: {sorted(missing)}"
        assert all(statuses[name] == "curated" for name in EXPECTED_CURATED)
        assert len(strategy_rows) == len(EXPECTED_CURATED)
        assert ability_count == 12
        assert dialogue_count == 41

        print("Bahsei DB snapshot health:", health)
        print("Expected Bahsei health:", EXPECTED_HEALTH)
        assert health == EXPECTED_HEALTH, (
            f"Bahsei health mismatch: actual={health!r}, expected={EXPECTED_HEALTH!r}"
        )

        # Re-import to prove replacement/upsert behavior does not duplicate data.
        store.save_boss(boss)
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_mechanic WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0] == len(mechanic_rows)
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_strategy WHERE encounter_id = ?", (boss.id,)
        ).fetchone()[0] == len(strategy_rows)

        print("BAHSEI DATABASE TEST PASSED")
        print(f"  test db:   {test_db}")
        print(f"  encounter: {boss.id}")
        print(f"  content:   {boss.content_id}")
        print(f"  abilities: {ability_count}")
        print(f"  mechanics: {len(mechanic_rows)}")
        print(f"  curated:   {len(EXPECTED_CURATED)}")
        print(f"  strategies:{len(strategy_rows)}")
        print(f"  dialogue:  {dialogue_count}")
        print(f"  health:    {health[0]} / {health[1]} / {health[2]}")
        print(f"  source rev:{boss.source.revision_id if boss.source else None}")
        print("  idempotent: yes")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
