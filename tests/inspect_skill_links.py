import sqlite3

db = sqlite3.connect(
    r".\data\eso.db"
)

rows = db.execute(
    """
    SELECT
        id,
        name,
        base_ability_id
    FROM skill
    WHERE name IN (
        'Pierce Armor',
        'Wall of Elements',
        'Aggressive Horn'
    )
    """
).fetchall()

for row in rows:
    print(row)

db.close()