import sqlite3

db = sqlite3.connect(r".\data\eso.db")

print("SKILL:")
for row in db.execute(
    """
    SELECT id, name, skill_line, base_ability_id
    FROM skill
    WHERE lower(name) = lower(?)
    """,
    ("Pariah's Resolve",),
):
    print(row)

print()
print("ENTITIES:")

for row in db.execute(
    """
    SELECT id, entity_type, name, slug
    FROM entity
    WHERE lower(name) = lower(?)
    """,
    ("Pariah's Resolve",),
):
    print(row)

db.close()