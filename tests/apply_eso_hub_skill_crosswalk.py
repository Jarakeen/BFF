import json
import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

CROSSWALK_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "eso_hub_skill_crosswalk_repaired.json"
)

DB_PATH = BASE_DIR / "data" / "eso.db"

REPORT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "eso_hub_skill_crosswalk_apply_report.json"
)


def slugify(value):
    value = str(value).casefold().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def canonical_skill_id(name, skill_line):
    if not isinstance(name, str) or not name.strip():
        return None

    if isinstance(skill_line, str) and skill_line.strip():
        return (
            "skill:"
            f"{slugify(skill_line)}:"
            f"{slugify(name)}"
        )

    return f"skill:{slugify(name)}"


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Skill Crosswalk Applier")
    print("=" * 60)
    print()
    print("DATABASE OPERATION: entity_source ONLY")
    print()

    if not CROSSWALK_PATH.exists():
        raise FileNotFoundError(
            f"Repaired crosswalk not found:\n{CROSSWALK_PATH}"
        )

    with CROSSWALK_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    repaired = data.get("repaired", [])

    if not isinstance(repaired, list):
        raise ValueError(
            "Crosswalk 'repaired' must be a list."
        )

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    applied = []
    skipped = []
    errors = []

    try:
        for item in repaired:
            if item.get("resolution") != "skill_match":
                skipped.append({
                    "index": item.get("index"),
                    "skill_name": item.get("skill_name"),
                    "reason": (
                        "Only direct skill matches are applied. "
                        "Ability-only matches remain evidence."
                    ),
                })
                continue

            match = item.get("skill_match") or {}
            skill_id = match.get("skill_id")
            skill_name = match.get("name")
            skill_line = match.get("skill_line")
            url = item.get("url")

            if skill_id is None or not skill_name:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": item.get("skill_name"),
                    "reason": "Missing skill match identity.",
                })
                continue

            if not url:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "reason": "Missing ESO-Hub URL.",
                })
                continue

            entity_id = canonical_skill_id(
                skill_name,
                skill_line,
            )

            if entity_id is None:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "reason": "Could not construct canonical skill ID.",
                })
                continue

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
                # Try to find the canonical entity by its
                # existing skill table identity before creating
                # anything. This prevents accidental duplicates.
                candidates = db.execute(
                    """
                    SELECT id, entity_type, name, slug
                    FROM entity
                    WHERE entity_type = 'skill'
                      AND lower(name) = lower(?)
                    """,
                    (skill_name,),
                ).fetchall()

                if len(candidates) == 1:
                    entity = candidates[0]
                    entity_id = entity["id"]
                else:
                    errors.append({
                        "index": item.get("index"),
                        "skill_name": skill_name,
                        "expected_entity_id": entity_id,
                        "reason": (
                            "Canonical skill entity not found "
                            "uniquely; no entity created."
                        ),
                    })
                    continue

            if entity["entity_type"] != "skill":
                errors.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "entity_id": entity_id,
                    "reason": (
                        "Resolved entity exists but is not "
                        "entity_type='skill'."
                    ),
                })
                continue

            existing = db.execute(
                """
                SELECT
                    id,
                    entity_id,
                    source,
                    source_entity_type,
                    source_id,
                    source_name
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
                applied.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "entity_id": entity_id,
                    "url": url,
                    "action": "already_present",
                    "entity_source_id": existing["id"],
                })
                continue

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
                    skill_name,
                    json.dumps(
                        item,
                        ensure_ascii=False,
                    ),
                ),
            )

            new_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            applied.append({
                "index": item.get("index"),
                "skill_name": skill_name,
                "entity_id": entity_id,
                "url": url,
                "action": "inserted",
                "entity_source_id": new_id,
            })

        db.commit()

        inserted = sum(
            1
            for row in applied
            if row["action"] == "inserted"
        )
        already_present = sum(
            1
            for row in applied
            if row["action"] == "already_present"
        )

        report = {
            "source_crosswalk": str(CROSSWALK_PATH),
            "database": str(DB_PATH),
            "summary": {
                "repaired_records": len(repaired),
                "applied_records": len(applied),
                "inserted": inserted,
                "already_present": already_present,
                "skipped": len(skipped),
                "errors": len(errors),
            },
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
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
        print(" APPLY SUMMARY")
        print("=" * 60)
        print()
        print(
            f"Repaired records:       {len(repaired)}"
        )
        print(
            f"Applied:                {len(applied)}"
        )
        print(
            f"Inserted mappings:      {inserted}"
        )
        print(
            f"Already present:        {already_present}"
        )
        print(
            f"Skipped:                {len(skipped)}"
        )
        print(
            f"Errors:                 {len(errors)}"
        )
        print()
        print(
            "Database changes: entity_source only"
        )
        print()
        print(
            f"Report: {REPORT_PATH}"
        )

        if errors:
            print()
            print("ERRORS:")
            for error in errors:
                print(
                    f"  {error['skill_name']}: "
                    f"{error['reason']}"
                )

        print()
        print("=" * 60)
        print(" CROSSWALK APPLY COMPLETE")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
