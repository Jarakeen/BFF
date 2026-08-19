import sqlite3

c = sqlite3.connect("data/eso.db")

print("=== LUCENT CONTENT ===")
print(
    c.execute(
        "SELECT id, name, content_type, group_size "
        "FROM content WHERE id = ?",
        ("lucent_citadel",),
    ).fetchone()
)

print()
print("=== LUCENT BOSSES ===")

rows = c.execute(
    """
    SELECT cb.position, b.id, b.name, b.content_id
    FROM content_bosses cb
    JOIN bosses b ON b.id = cb.boss_id
    WHERE cb.content_id = ?
    ORDER BY cb.position
    """,
    ("lucent_citadel",),
).fetchall()

for row in rows:
    print(row)

print()
print("=== LUCENT SETS ===")

rows = c.execute(
    "SELECT * FROM content_sets WHERE content_id = ?",
    ("lucent_citadel",),
).fetchall()

for row in rows:
    print(row)

print()
print("=== LUCENT ACHIEVEMENTS ===")

rows = c.execute(
    """
    SELECT achievement_id, name, points
    FROM content_achievements
    WHERE content_id = ?
    ORDER BY position
    """,
    ("lucent_citadel",),
).fetchall()

for row in rows:
    print(row)

print()
print("=== BOSS HEALTH ===")

boss_ids = (
    "count_ryelaz",
    "zilyesset",
    "cavot_agnan",
    "orphic_shattered_shard",
    "xoryn",
)

rows = c.execute(
    """
    SELECT id, name, content_id,
           health_normal,
           health_veteran,
           health_hardmode
    FROM bosses
    WHERE id IN (?, ?, ?, ?, ?)
    ORDER BY id
    """,
    boss_ids,
).fetchall()

for row in rows:
    print(row)

c.close()
