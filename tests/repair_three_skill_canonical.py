import json
import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "eso.db"

CROSSWALK_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "eso_hub_skill_crosswalk_repaired.json"
)

REPORT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "eso_hub_three_skill_canonical_repair_report.json"
)


REPAIRS = [
    {
        "skill_id": 672,
        "entity_id": "skill:heavy_armor:resolve",
        "name": "Resolve",
    },
    {
        "skill_id": 782,
        "entity_id": "skill:argonian_skills:resourceful",
        "name": "Resourceful",
    },
    {
        "skill_id": 975,
        "entity_id": "skill:volendrung:pariahs_resolve",
        "name": "Pariah's Resolve",
    },
]


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Three Skill Canonical Repair")
    print("=" * 60)
    print()
    print("DATABASE OPERATION:")
    print("  entity + entity_source")
    print("ONLY the three verified skills")
    print()

    if not CROSSWALK_PATH.exists():
        raise FileNotFoundError(
            f"Repaired crosswalk not found:\n{CROSSWALK_PATH}"
        )

    with CROSSWALK_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        crosswalk = json.load(handle)

    repaired_records = {
        item.get("skill_name"): item
        for item in crosswalk.get("repaired", [])
        if item.get("resolution") == "skill_match"
    }

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    entity_actions = []
    mapping_actions = []
    errors = []

    try:
        for repair in REPAIRS:

            skill_id = repair["skill_id"]
            expected_name = repair["name"]
            entity_id = repair["entity_id"]

            # ------------------------------------------------
            # Verify internal skill.
            # ------------------------------------------------

            skill = db.execute(
                """
                SELECT
                    id,
                    name,
                    skill_line,
                    base_ability_id
                FROM skill
                WHERE id = ?
                """,
                (skill_id,),
            ).fetchone()

            if skill is None:
                errors.append({
                    "name": expected_name,
                    "reason": (
                        f"Internal skill {skill_id} "
                        "does not exist."
                    ),
                })
                continue

            if skill["name"] != expected_name:
                errors.append({
                    "name": expected_name,
                    "reason": (
                        f"Skill {skill_id} is "
                        f"{skill['name']!r}, not "
                        f"{expected_name!r}."
                    ),
                })
                continue

            # ------------------------------------------------
            # Verify/create canonical entity.
            # ------------------------------------------------

            entity = db.execute(
                """
                SELECT
                    id,
                    entity_type,
                    name,
                    slug
                FROM entity
                WHERE id = ?
                """,
                (entity_id,),
            ).fetchone()

            if entity is None:

                slug = entity_id.split(
                    ":",
                    1,
                )[-1]

                db.execute(
                    """
                    INSERT INTO entity (
                        id,
                        entity_type,
                        name,
                        slug
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        "skill",
                        expected_name,
                        slug,
                    ),
                )

                entity_actions.append({
                    "action": "created",
                    "entity_id": entity_id,
                    "skill_id": skill_id,
                    "name": expected_name,
                })

            else:

                if entity["entity_type"] != "skill":
                    errors.append({
                        "name": expected_name,
                        "entity_id": entity_id,
                        "reason": (
                            "Existing entity has the "
                            f"wrong type: "
                            f"{entity['entity_type']}"
                        ),
                    })
                    continue

                if entity["name"] != expected_name:
                    errors.append({
                        "name": expected_name,
                        "entity_id": entity_id,
                        "reason": (
                            "Existing entity has a "
                            f"different name: "
                            f"{entity['name']!r}"
                        ),
                    })
                    continue

                entity_actions.append({
                    "action": "already_present",
                    "entity_id": entity_id,
                    "skill_id": skill_id,
                    "name": expected_name,
                })

            # ------------------------------------------------
            # Find ESO-Hub source record.
            # ------------------------------------------------

            source_record = repaired_records.get(
                expected_name
            )

            if source_record is None:
                errors.append({
                    "name": expected_name,
                    "reason": (
                        "No repaired ESO-Hub record "
                        "found in crosswalk."
                    ),
                })
                continue

            url = source_record.get("url")

            if not url:
                errors.append({
                    "name": expected_name,
                    "reason": (
                        "Repaired record has no ESO-Hub URL."
                    ),
                })
                continue

            # ------------------------------------------------
            # Insert source mapping.
            # ------------------------------------------------

            existing = db.execute(
                """
                SELECT
                    id
                FROM entity_source
                WHERE entity_id = ?
                  AND source = 'ESO-Hub'
                  AND source_id = ?
                """,
                (
                    entity_id,
                    url,
                ),
            ).fetchone()

            if existing is not None:

                mapping_actions.append({
                    "action": "already_present",
                    "entity_id": entity_id,
                    "skill_id": skill_id,
                    "name": expected_name,
                    "url": url,
                    "entity_source_id": existing["id"],
                })

            else:

                db.execute(
                    """
                    INSERT INTO entity_source (
                        entity_id,
                        source,
                        source_entity_type,
                        source_id,
                        source_name,
                        raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        "ESO-Hub",
                        "skill",
                        url,
                        expected_name,
                        json.dumps(
                            source_record,
                            ensure_ascii=False,
                        ),
                    ),
                )

                source_id = db.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]

                mapping_actions.append({
                    "action": "inserted",
                    "entity_id": entity_id,
                    "skill_id": skill_id,
                    "name": expected_name,
                    "url": url,
                    "entity_source_id": source_id,
                })

        if errors:
            db.rollback()

            print("=" * 60)
            print(" REPAIR ABORTED")
            print("=" * 60)
            print()

            for error in errors:
                print(
                    f"{error['name']}: "
                    f"{error['reason']}"
                )

            print()
            print(
                "No database changes were committed."
            )

            raise RuntimeError(
                "Three-skill canonical repair failed."
            )

        db.commit()

        report = {
            "database": str(DB_PATH),
            "crosswalk": str(CROSSWALK_PATH),
            "repairs": REPAIRS,
            "entity_actions": entity_actions,
            "mapping_actions": mapping_actions,
            "errors": errors,
            "summary": {
                "skills_verified": len(REPAIRS),
                "entities_created": sum(
                    1
                    for item in entity_actions
                    if item["action"] == "created"
                ),
                "entities_existing": sum(
                    1
                    for item in entity_actions
                    if item["action"]
                    == "already_present"
                ),
                "mappings_inserted": sum(
                    1
                    for item in mapping_actions
                    if item["action"] == "inserted"
                ),
                "mappings_existing": sum(
                    1
                    for item in mapping_actions
                    if item["action"]
                    == "already_present"
                ),
                "errors": len(errors),
            },
        }

        REPORT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with REPORT_PATH.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                report,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        print("=" * 60)
        print(" THREE-SKILL REPAIR COMPLETE")
        print("=" * 60)
        print()

        for item in entity_actions:
            print(
                f"ENTITY {item['action']:16} "
                f"{item['entity_id']}"
            )

        for item in mapping_actions:
            print(
                f"MAPPING {item['action']:15} "
                f"{item['name']}"
            )

        print()
        print(
            f"Skills verified:       {len(REPAIRS)}"
        )
        print(
            "Entities created:      "
            f"{report['summary']['entities_created']}"
        )
        print(
            "Mappings inserted:     "
            f"{report['summary']['mappings_inserted']}"
        )
        print(
            f"Errors:                {len(errors)}"
        )
        print()
        print(
            f"Report: {REPORT_PATH}"
        )

    except Exception:
        # If an exception happens before the explicit rollback,
        # make sure the transaction cannot partially persist.
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
