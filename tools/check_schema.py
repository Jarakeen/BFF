from pathlib import Path
import sys

# Make the FoundryDock project root importable when this file
# is executed directly from tools/.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.eso_db.schema import connect, SCHEMA_VERSION


DB_PATH = ROOT / "data" / "eso.db"

connection = connect(DB_PATH)

print("DATABASE:", DB_PATH)
print("SCHEMA VERSION:", SCHEMA_VERSION)

print(
    "CONTENT COLUMNS:",
    [row[1] for row in connection.execute("PRAGMA table_info(content)")],
)

print(
    "CONTENT SETS:",
    connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='content_sets'"
    ).fetchone(),
)

print(
    "SCHEMA VERSION ROW:",
    connection.execute(
        "SELECT version FROM schema_version"
    ).fetchone(),
)

connection.close()