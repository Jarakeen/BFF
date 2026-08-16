import sqlite3

db = sqlite3.connect("data/eso.db")
db.row_factory = sqlite3.Row

print("\n=== EFFECTS FOR POWERFUL ASSAULT ===")

rows = db.execute(
    """
    SELECT
        e.id AS effect_id,
        e.name AS effect_name,
        e.category,
        ev.id AS variant_id,
        ev.type AS variant_type,
        ev.description AS variant_description,
        es.id AS source_id,
        es.source_type,
        es.source_name,
        es.condition,
        es.raw_text
    FROM effect_source es
    JOIN effect_variant ev
        ON ev.id = es.effect_variant_id
    JOIN effect e
        ON e.id = ev.effect_id
    WHERE lower(es.source_name) LIKE '%powerful assault%'
       OR lower(es.raw_text) LIKE '%powerful assault%'
    ORDER BY e.id, ev.id, es.id
    """
).fetchall()

for row in rows:
    print(dict(row))

db.close()