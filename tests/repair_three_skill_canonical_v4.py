import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "eso.db"
ESO_HUB_PATH = BASE_DIR / "data" / "raw" / "eso_hub_skill_data.json"
REPORT_PATH = BASE_DIR / "data" / "processed" / "three_skill_canonical_repair_v4_report.json"

REPAIRS = [
    (672, "Resolve", "Resolve Skill", "Heavy Armor",
     "skill:heavy_armor:resolve"),
    (782, "Resourceful", "Resourceful Skill", "Argonian Skills",
     "skill:argonian_skills:resourceful"),
    (975, "Pariah's Resolve", "Pariah's Resolve Skill", "Volendrung",
     "skill:volendrung:pariahs_resolve"),
]


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Three Skill Canonical Repair v4")
    print("=" * 60)
    print()
    print("Uses the verified ESO-Hub names from the source.")
    print("Does NOT read the crosswalk.")
    print()

    with ESO_HUB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    records = data["skills"] if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError("ESO-Hub source does not contain a skills list.")

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    actions = []
    errors = []

    try:
        for skill_id, internal_name, eso_name, skill_line, entity_id in REPAIRS:
            skill = db.execute(
                """
                SELECT id, name, skill_line, base_ability_id
                FROM skill
                WHERE id = ?
                """,
                (skill_id,),
            ).fetchone()

            if skill is None:
                errors.append(f"{internal_name}: skill {skill_id} does not exist")
                continue

            if skill["name"] != internal_name:
                errors.append(
                    f"{internal_name}: skill {skill_id} is {skill['name']!r}"
                )
                continue

            if skill["skill_line"] != skill_line:
                errors.append(
                    f"{internal_name}: skill line is "
                    f"{skill['skill_line']!r}, expected {skill_line!r}"
                )
                continue

            matches = [
                r for r in records
                if isinstance(r, dict)
                and r.get("skill_name") == eso_name
            ]

            if len(matches) != 1:
                errors.append(
                    f"{internal_name}: expected exactly one ESO-Hub "
                    f"record named {eso_name!r}, found {len(matches)}"
                )
                continue

            source_record = matches[0]
            url = source_record.get("eso_hub_url")

            if not url:
                errors.append(f"{internal_name}: ESO-Hub URL missing")
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
                    (entity_id, internal_name, slug),
                )
                entity_action = "created"
            else:
                if entity["entity_type"] != "skill":
                    errors.append(
                        f"{internal_name}: {entity_id} has type "
                        f"{entity['entity_type']!r}"
                    )
                    continue
                if entity["name"] != internal_name:
                    errors.append(
                        f"{internal_name}: {entity_id} has name "
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
                        internal_name,
                        json.dumps(source_record, ensure_ascii=False),
                    ),
                )
                source_row_id = db.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]
                mapping_action = "inserted"

            actions.append({
                "skill_id": skill_id,
                "name": internal_name,
                "eso_hub_name": eso_name,
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
        for x in actions:
            print(
                f"{x['name']}: "
                f"entity={x['entity_action']}, "
                f"mapping={x['mapping_action']}"
            )
        print()
        print(f"Skills verified:    {len(actions)}")
        print(f"Entities created:   {report['summary']['entities_created']}")
        print(f"Mappings inserted:  {report['summary']['mappings_inserted']}")
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
