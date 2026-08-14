import json
import re
import sqlite3
from pathlib import Path


BASE_DIR = (
    Path(__file__).resolve().parent.parent
)

DB_PATH = (
    BASE_DIR
    / "data"
    / "eso.db"
)

SOURCE_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "eso_hub_skill_data.json"
)


def slugify(value: str) -> str:

    value = value.strip().casefold()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


def skill_identity(
    url: str,
    name: str,
) -> tuple[str, str]:

    marker = "/en/skills/"

    if (
        isinstance(url, str)
        and marker in url
    ):

        path = url.split(
            marker,
            1,
        )[1]

        path = path.split(
            "?",
            1,
        )[0]

        path = path.split(
            "#",
            1,
        )[0]

        parts = [
            slugify(part)
            for part in path.split("/")
            if part.strip()
        ]

        if parts:

            hierarchy = ":".join(
                parts
            )

            slug = "_".join(
                parts
            )

            return (
                f"skill:{hierarchy}",
                slug,
            )

    name_slug = slugify(name)

    return (
        f"skill:{name_slug}",
        name_slug,
    )


def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Skill Identity Repair")
    print("=" * 60)
    print()

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    records = data["skills"]

    db = sqlite3.connect(
        DB_PATH
    )

    try:

        db.execute(
            "PRAGMA foreign_keys = ON"
        )

        repaired = 0
        already_correct = 0

        # ----------------------------------------------------
        # First pass:
        # create/update the correct canonical identities
        # ----------------------------------------------------

        for record in records:

            name = record.get(
                "skill_name"
            )

            url = record.get(
                "eso_hub_url"
            )

            if not isinstance(
                name,
                str,
            ):
                continue

            if not isinstance(
                url,
                str,
            ):
                continue

            new_id, new_slug = (
                skill_identity(
                    url,
                    name,
                )
            )

            existing = db.execute(
                """
                SELECT id
                FROM entity
                WHERE id = ?
                """,
                (new_id,),
            ).fetchone()

            if existing is None:

                db.execute(
                    """
                    INSERT INTO entity (
                        id,
                        entity_type,
                        name,
                        slug
                    )
                    VALUES (
                        ?, ?, ?, ?
                    )
                    """,
                    (
                        new_id,
                        "skill",
                        name,
                        new_slug,
                    ),
                )

                repaired += 1

            else:

                db.execute(
                    """
                    UPDATE entity
                    SET
                        name = ?,
                        slug = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        new_slug,
                        new_id,
                    ),
                )

                already_correct += 1

            # ------------------------------------------------
            # Move this exact ESO-Hub source mapping.
            #
            # This is important because both Executioner
            # records previously shared skill:executioner.
            # We distinguish them by their ESO-Hub URL.
            # ------------------------------------------------

            db.execute(
                """
                UPDATE entity_source
                SET entity_id = ?
                WHERE source = 'ESO-Hub'
                  AND source_entity_type = 'skill'
                  AND source_id = ?
                """,
                (
                    new_id,
                    url,
                ),
            )

        # ----------------------------------------------------
        # Remove the old name-only skill identity.
        #
        # We only remove it if it is no longer referenced.
        # ----------------------------------------------------

        old_id = "skill:executioner"

        remaining_sources = db.execute(
            """
            SELECT COUNT(*)
            FROM entity_source
            WHERE entity_id = ?
            """,
            (old_id,),
        ).fetchone()[0]

        if remaining_sources == 0:

            db.execute(
                """
                DELETE FROM entity
                WHERE id = ?
                """,
                (old_id,),
            )

            print(
                "Removed old canonical ID:"
            )

            print(
                f"  {old_id}"
            )

        else:

            print(
                "WARNING:"
            )

            print(
                f"  {old_id} still has "
                f"{remaining_sources} source mappings."
            )

        db.commit()

        print()
        print(
            f"Records inspected: "
            f"{len(records)}"
        )

        print(
            f"New identities created: "
            f"{repaired}"
        )

        print(
            f"Existing identities updated: "
            f"{already_correct}"
        )

        print()
        print(
            "EXECUTIONER IDENTITIES:"
        )

        rows = db.execute(
            """
            SELECT
                id,
                entity_type,
                name,
                slug
            FROM entity
            WHERE entity_type = 'skill'
              AND name = 'Executioner'
            ORDER BY id
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row}"
            )

        print()
        print(
            "EXECUTIONER SOURCE MAPPINGS:"
        )

        rows = db.execute(
            """
            SELECT
                entity_id,
                source,
                source_id,
                source_name
            FROM entity_source
            WHERE source = 'ESO-Hub'
              AND source_entity_type = 'skill'
              AND source_name = 'Executioner'
            ORDER BY source_id
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row}"
            )

        print()
        print("=" * 60)
        print(" SKILL IDENTITY REPAIR COMPLETE")
        print("=" * 60)

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()