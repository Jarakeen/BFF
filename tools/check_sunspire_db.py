from pathlib import Path
import sys
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "eso.db"

connection = sqlite3.connect(DB_PATH)

print("=" * 70)
print("SUNSPIRE CONTENT")
print("=" * 70)

row = connection.execute(
    """
    SELECT id, name, content_type, group_size
    FROM content
    WHERE id = 'sunspire'
    """
).fetchone()

print(row)

print("\n" + "=" * 70)
print("SUNSPIRE BOSSES")
print("=" * 70)

rows = connection.execute(
    """
    SELECT cb.position, cb.boss_id, b.name
    FROM content_bosses cb
    JOIN bosses b ON b.id = cb.boss_id
    WHERE cb.content_id = 'sunspire'
    ORDER BY cb.position
    """
).fetchall()

for row in rows:
    print(row)

print("\n" + "=" * 70)
print("SUNSPIRE SETS")
print("=" * 70)

rows = connection.execute(
    """
    SELECT position, set_id
    FROM content_sets
    WHERE content_id = 'sunspire'
    ORDER BY position
    """
).fetchall()

for row in rows:
    print(row)

print("\n" + "=" * 70)
print("SUNSPIRE ACHIEVEMENTS")
print("=" * 70)

rows = connection.execute(
    """
    SELECT position, achievement_id, name
    FROM content_achievements
    WHERE content_id = 'sunspire'
    ORDER BY position
    """
).fetchall()

for row in rows:
    print(row)

connection.close()