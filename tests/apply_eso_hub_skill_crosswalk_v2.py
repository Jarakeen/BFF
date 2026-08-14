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
    / "eso_hub_skill_crosswalk_v2_apply_report.json"
)


def slugify(value):
    if not isinstance(value, str):
        return ""

    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize(value):
    if not isinstance(value, str):
        return ""

    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def contextual_entity_ids(
    name,
    skill_line,
):
    name_slug = slugify(name)
    line_slug = slugify(skill_line)

    if not name_slug:
        return []

    ids = []

    if line_slug:
        ids.append(
            f"skill:{line_slug}:{name_slug}"
        )

    ids.append(
        f"skill:{name_slug}"
    )

    return ids


def find_entity_for_skill(
    db,
    skill_id,
    skill_name,
    skill_line,
):
    """
    Resolve an existing canonical skill entity.

    The internal skill_id is the authoritative anchor.
    The canonical entity is selected using the actual
    internal skill name + skill line.

    No entities are created here.
    """

    # --------------------------------------------------------
    # First: contextual canonical ID
    # --------------------------------------------------------

    candidate_ids = contextual_entity_ids(
        skill_name,
        skill_line,
    )

    for entity_id in candidate_ids:

        row = db.execute(
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

        if row is None:
            continue

        if row["entity_type"] != "skill":
            continue

        return {
            "entity_id": row["id"],
            "entity_type": row["entity_type"],
            "name": row["name"],
            "slug": row["slug"],
            "method": "contextual_id",
        }

    # --------------------------------------------------------
    # Second: search by exact name and validate slug
    # --------------------------------------------------------

    rows = db.execute(
        """
        SELECT
            id,
            entity_type,
            name,
            slug
        FROM entity
        WHERE entity_type = 'skill'
          AND lower(name) = lower(?)
        ORDER BY id
        """,
        (skill_name,),
    ).fetchall()

    if not rows:
        return None

    expected_line = slugify(
        skill_line
    )

    contextual = []

    for row in rows:
        slug = row["slug"] or ""

        if expected_line and slug.startswith(
            expected_line + "_"
        ):
            contextual.append(row)

    if len(contextual) == 1:
        row = contextual[0]

        return {
            "entity_id": row["id"],
            "entity_type": row["entity_type"],
            "name": row["name"],
            "slug": row["slug"],
            "method": "contextual_slug",
        }

    # --------------------------------------------------------
    # Generic entity is acceptable only if there is exactly
    # one skill entity with this name.
    # --------------------------------------------------------

    if len(rows) == 1:
        row = rows[0]

        return {
            "entity_id": row["id"],
            "entity_type": row["entity_type"],
            "name": row["name"],
            "slug": row["slug"],
            "method": "unique_generic",
        }

    return {
        "ambiguous": True,
        "candidates": [
            {
                "entity_id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
            }
            for row in rows
        ],
    }


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Skill Crosswalk Applier v2")
    print("=" * 60)
    print()
    print("DATABASE OPERATION: entity_source ONLY")
    print("NO CANONICAL ENTITIES WILL BE CREATED")
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

    repaired = data.get(
        "repaired",
        [],
    )

    if not isinstance(repaired, list):
        raise ValueError(
            "Crosswalk 'repaired' must be a list."
        )

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    applied = []
    already_present = []
    skipped = []
    ambiguous = []
    errors = []

    try:
        for item in repaired:

            # Only direct skill matches are safe to apply
            # at this stage.
            if item.get("resolution") != "skill_match":
                skipped.append({
                    "index": item.get("index"),
                    "skill_name": item.get("skill_name"),
                    "reason": (
                        "Not a direct skill match."
                    ),
                })
                continue

            match = item.get(
                "skill_match"
            ) or {}

            internal_skill_id = match.get(
                "skill_id"
            )

            if internal_skill_id is None:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": item.get("skill_name"),
                    "reason": (
                        "Crosswalk has no internal skill_id."
                    ),
                })
                continue

            # ------------------------------------------------
            # Internal skill is the authoritative anchor.
            # ------------------------------------------------

            skill_row = db.execute(
                """
                SELECT
                    id,
                    name,
                    skill_line,
                    base_ability_id
                FROM skill
                WHERE id = ?
                """,
                (internal_skill_id,),
            ).fetchone()

            if skill_row is None:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": item.get("skill_name"),
                    "skill_id": internal_skill_id,
                    "reason": (
                        "Internal skill_id does not exist."
                    ),
                })
                continue

            skill_name = skill_row["name"]
            skill_line = skill_row["skill_line"]
            base_ability_id = skill_row[
                "base_ability_id"
            ]

            # ------------------------------------------------
            # Resolve existing canonical entity.
            # ------------------------------------------------

            entity = find_entity_for_skill(
                db,
                internal_skill_id,
                skill_name,
                skill_line,
            )

            if entity is None:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "skill_id": internal_skill_id,
                    "skill_line": skill_line,
                    "reason": (
                        "No existing canonical skill "
                        "entity could be resolved."
                    ),
                })
                continue

            if entity.get("ambiguous"):
                ambiguous.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "skill_id": internal_skill_id,
                    "skill_line": skill_line,
                    "candidates": entity[
                        "candidates"
                    ],
                })
                continue

            entity_id = entity[
                "entity_id"
            ]

            url = item.get(
                "url"
            )

            if not url:
                errors.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "skill_id": internal_skill_id,
                    "entity_id": entity_id,
                    "reason": (
                        "Missing ESO-Hub URL."
                    ),
                })
                continue

            # ------------------------------------------------
            # Check existing source mapping.
            # ------------------------------------------------

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

                already_present.append({
                    "index": item.get("index"),
                    "skill_name": skill_name,
                    "skill_id": internal_skill_id,
                    "base_ability_id":
                        base_ability_id,
                    "entity_id": entity_id,
                    "url": url,
                    "entity_source_id":
                        existing["id"],
                    "method": entity["method"],
                })

                continue

            # ------------------------------------------------
            # Insert source mapping only.
            # ------------------------------------------------

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

            source_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            applied.append({
                "index": item.get("index"),
                "skill_name": skill_name,
                "skill_id": internal_skill_id,
                "base_ability_id":
                    base_ability_id,
                "skill_line": skill_line,
                "entity_id": entity_id,
                "url": url,
                "entity_source_id": source_id,
                "method": entity["method"],
            })

        db.commit()

        report = {
            "source_crosswalk": str(
                CROSSWALK_PATH
            ),
            "database": str(DB_PATH),
            "summary": {
                "repaired_records": len(repaired),
                "inserted": len(applied),
                "already_present":
                    len(already_present),
                "skipped": len(skipped),
                "ambiguous": len(ambiguous),
                "errors": len(errors),
            },
            "inserted": applied,
            "already_present":
                already_present,
            "skipped": skipped,
            "ambiguous": ambiguous,
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
            f"Inserted mappings:      {len(applied)}"
        )
        print(
            f"Already present:        "
            f"{len(already_present)}"
        )
        print(
            f"Skipped:                {len(skipped)}"
        )
        print(
            f"Ambiguous:              {len(ambiguous)}"
        )
        print(
            f"Errors:                 {len(errors)}"
        )
        print()
        print(
            "Database changes: entity_source only"
        )
        print(
            f"Report: {REPORT_PATH}"
        )

        if ambiguous:
            print()
            print("AMBIGUOUS:")
            for item in ambiguous:
                print(
                    f"  {item['skill_name']} "
                    f"(skill {item['skill_id']})"
                )
                for candidate in item[
                    "candidates"
                ]:
                    print(
                        f"    {candidate['entity_id']}"
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
        print(" CROSSWALK APPLY V2 COMPLETE")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
