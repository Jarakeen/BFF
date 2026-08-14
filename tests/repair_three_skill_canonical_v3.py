import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "eso.db"
ESO_HUB_PATH = BASE_DIR / "data" / "raw" / "eso_hub_skill_data.json"
REPORT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "three_skill_canonical_repair_v3_report.json"
)

REPAIRS = [
    (672, "Resolve", "Heavy Armor", "skill:heavy_armor:resolve"),
    (782, "Resourceful", "Argonian Skills", "skill:argonian_skills:resourceful"),
    (975, "Pariah's Resolve", "Volendrung", "skill:volendrung:pariahs_resolve"),
]


def values_matching(record, target):
    """Find exact target-string values anywhere inside a JSON record."""
    found = []

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{path}[{i}]")
        elif isinstance(value, str) and value.strip() == target:
            found.append(path)

    walk(record)
    return found


def find_url(record):
    """Find the most likely URL field anywhere in a JSON record."""
    candidates = []

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, child in value.items():
                key_lower = str(key).lower()
                if (
                    isinstance(child, str)
                    and (
                        "url" in key_lower
                        or "link" in key_lower
                    )
                    and "eso-hub.com" in child
                ):
                    candidates.append((path, child))
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, f"{path}[{i}]")

    walk(record)

    # Prefer the actual skill page URL over category/skill-line URLs.
    skill_urls = [
        item for item in candidates
        if "/skills/" in item[1]
    ]
    if skill_urls:
        return skill_urls[0][1]

    return candidates[0][1] if candidates else None


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Three Skill Canonical Repair v3")
    print("=" * 60)
    print()
    print("Reads ESO-Hub directly.")
    print("Does NOT read the crosswalk.")
    print("Does NOT assume a field named skill_name.")
    print()

    with ESO_HUB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("skills", []) if isinstance(data, dict) else data

    if not isinstance(records, list):
        raise ValueError("ESO-Hub source does not contain a skills list.")

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    actions = []
    errors = []

    try:
        for skill_id, name, skill_line, entity_id in REPAIRS:
            skill = db.execute(
                """
                SELECT id, name, skill_line, base_ability_id
                FROM skill
                WHERE id = ?
                """,
                (skill_id,),
            ).fetchone()

            if skill is None:
                errors.append(f"{name}: skill {skill_id} does not exist")
                continue

            if skill["name"] != name:
                errors.append(
                    f"{name}: skill {skill_id} is {skill['name']!r}"
                )
                continue

            if skill["skill_line"] != skill_line:
                errors.append(
                    f"{name}: skill line is {skill['skill_line']!r}, "
                    f"expected {skill_line!r}"
                )
                continue

            matches = [
                record
                for record in records
                if values_matching(record, name)
            ]

            if len(matches) != 1:
                errors.append(
                    f"{name}: expected exactly one ESO-Hub record "
                    f"containing this exact name, found {len(matches)}"
                )
                continue

            source_record = matches[0]
            url = find_url(source_record)

            if not url:
                errors.append(
                    f"{name}: no ESO-Hub URL found in matching record"
                )
                continue

            entity = db.execute(
                """
                SELECT id, entity_type, name, slug
                FROM entity
                WHERE id = ?
                """,
                (entity_id,),
            ).fetchone()

            if entity is None:
                slug = entity_id.rsplit(":", 1)[-1]

                db.execute(
                    """
                    INSERT INTO entity
                        (id, entity_type, name, slug)
                    VALUES (?, 'skill', ?, ?)
                    """,
                    (entity_id, name, slug),
                )
                entity_action = "created"
            else:
                if entity["entity_type"] != "skill":
                    errors.append(
                        f"{name}: {entity_id} has type "
                        f"{entity['entity_type']!r}"
                    )
                    continue

                if entity["name"] != name:
                    errors.append(
                        f"{name}: {entity_id} has name "
                        f"{entity['name']!r}"
                    )
                    continue

                entity_action = "already_present"

            existing = db.execute(
                """
                SELECT id
                FROM entity_source
                WHERE entity_id = ?
                  AND source = 'ESO-Hub'
                  AND source_id = ?
                """,
                (entity_id, url),
            ).fetchone()

            if existing:
                mapping_action = "already_present"
                source_row_id = existing["id"]
            else:
                db.execute(
                    """
                    INSERT INTO entity_source
                        (entity_id, source, source_entity_type,
                         source_id, source_name, raw_json)
                    VALUES (?, 'ESO-Hub', 'skill', ?, ?, ?)
                    """,
                    (
                        entity_id,
                        url,
                        name,
                        json.dumps(source_record, ensure_ascii=False),
                    ),
                )

                source_row_id = db.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]

                mapping_action = "inserted"

            actions.append({
                "skill_id": skill_id,
                "name": name,
                "skill_line": skill_line,
                "base_ability_id": skill["base_ability_id"],
                "entity_id": entity_id,
                "entity_action": entity_action,
                "mapping_action": mapping_action,
                "entity_source_id": source_row_id,
                "url": url,
            })

        if errors:
            db.rollback()

            print("=" * 60)
            print(" REPAIR ABORTED")
            print("=" * 60)
            print()

            for error in errors:
                print(f"  {error}")

            print()
            print("No database changes were committed.")
            raise RuntimeError("Three-skill canonical repair failed.")

        db.commit()

        report = {
            "summary": {
                "verified": len(actions),
                "entities_created": sum(
                    x["entity_action"] == "created" for x in actions
                ),
                "mappings_inserted": sum(
                    x["mapping_action"] == "inserted" for x in actions
                ),
                "errors": 0,
            },
            "actions": actions,
        }

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with REPORT_PATH.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print("=" * 60)
        print(" THREE-SKILL REPAIR COMPLETE")
        print("=" * 60)
        print()

        for action in actions:
            print(
                f"{action['name']}: "
                f"entity={action['entity_action']}, "
                f"mapping={action['mapping_action']}"
            )

        print()
        print(f"Skills verified:    {len(actions)}")
        print(
            "Entities created:   "
            f"{report['summary']['entities_created']}"
        )
        print(
            "Mappings inserted:  "
            f"{report['summary']['mappings_inserted']}"
        )
        print("Errors:             0")
        print()
        print(f"Report: {REPORT_PATH}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
