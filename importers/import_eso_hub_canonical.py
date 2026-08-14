import json
import re
import sqlite3
from pathlib import Path


# ============================================================
# Paths
# ============================================================

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


# ============================================================
# Identity Helpers
# ============================================================


def slugify(value: str) -> str:
    """
    Convert a display name or URL component into
    a stable canonical slug.
    """

    value = value.strip().casefold()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


def canonical_id(
    entity_type: str,
    name: str,
) -> str:
    """
    Build Foundry's canonical ID for non-skill
    entities.
    """

    return (
        f"{entity_type}:"
        f"{slugify(name)}"
    )


def skill_identity(
    url: str,
    name: str,
) -> tuple[str, str]:
    """
    Build a canonical skill ID and slug from
    the ESO-Hub URL hierarchy.

    Example:

        https://eso-hub.com/en/skills/
        nightblade/assassination/executioner

    becomes:

        ID:
        skill:nightblade:assassination:executioner

        slug:
        nightblade_assassination_executioner
    """

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

    # Safe fallback if the URL is unavailable.
    fallback = slugify(name)

    return (
        f"skill:{fallback}",
        fallback,
    )


# ============================================================
# Entity Helpers
# ============================================================


def ensure_entity(
    db,
    entity_type: str,
    name: str,
    source_url: str | None = None,
):
    """
    Insert or update a canonical entity.

    Skills use their ESO-Hub URL hierarchy.
    All other entity types use name-based identity.
    """

    if entity_type == "skill":

        entity_id, slug = skill_identity(
            source_url or "",
            name,
        )

    else:

        entity_id = canonical_id(
            entity_type,
            name,
        )

        slug = slugify(name)

    db.execute(
        """
        INSERT INTO entity (
            id,
            entity_type,
            name,
            slug
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            name = excluded.name,
            slug = excluded.slug
        """,
        (
            entity_id,
            entity_type,
            name,
            slug,
        ),
    )

    return entity_id


def ensure_source_mapping(
    db,
    entity_id: str,
    source: str,
    source_entity_type: str,
    source_id,
    source_name: str,
    raw_json=None,
):
    """
    Insert or update a source identity mapping.

    Source IDs are deliberately stored as TEXT.
    """

    if source_id is None:
        return

    source_id = str(
        source_id
    ).strip()

    if not source_id:
        return

    raw_value = None

    if raw_json is not None:

        raw_value = json.dumps(
            raw_json,
            ensure_ascii=False,
            sort_keys=True,
        )

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

        ON CONFLICT(
            entity_id,
            source,
            source_entity_type,
            source_id
        )
        DO UPDATE SET
            source_name = excluded.source_name,
            raw_json = excluded.raw_json
        """,
        (
            entity_id,
            source,
            source_entity_type,
            source_id,
            source_name,
            raw_value,
        ),
    )


# ============================================================
# Skill Import
# ============================================================


def import_skill_entity(
    db,
    record,
):
    """
    Import the skill itself as a canonical entity.

    Skills use their ESO-Hub URL hierarchy so that
    duplicate display names remain distinct.

    Example:

        Nightblade Executioner
        Weapon Executioner

    become two different canonical entities.
    """

    name = record.get(
        "skill_name"
    )

    if not isinstance(
        name,
        str,
    ):
        return False

    name = name.strip()

    if not name:
        return False

    url = record.get(
        "eso_hub_url"
    )

    entity_id = ensure_entity(
        db,
        "skill",
        name,
        source_url=url,
    )

    raw_json = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
    )

    ensure_source_mapping(
        db=db,
        entity_id=entity_id,
        source="ESO-Hub",
        source_entity_type="skill",
        source_id=url,
        source_name=name,
        raw_json=record,
    )

    return True


# ============================================================
# Relationship Entity Import
# ============================================================


def import_relationship_entities(
    db,
    record,
):
    """
    Import the canonical entities represented
    by ESO-Hub relationships.

    This pass deliberately does NOT create
    relationship rows between entities.
    """

    relationship_types = {
        "buffs": "buff",
        "debuffs": "debuff",
        "status_effects": "status_effect",
        "modifying_sets": "gear_set",
        "champion_points": "champion_point",
    }

    for field, entity_type in (
        relationship_types.items()
    ):

        items = record.get(
            field,
            [],
        )

        if not isinstance(
            items,
            list,
        ):
            continue

        for item in items:

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = item.get(
                "name"
            )

            if not isinstance(
                name,
                str,
            ):
                continue

            name = name.strip()

            if not name:
                continue

            entity_id = ensure_entity(
                db,
                entity_type,
                name,
            )

            url = item.get(
                "url"
            )

            ensure_source_mapping(
                db=db,
                entity_id=entity_id,
                source="ESO-Hub",
                source_entity_type=entity_type,
                source_id=url,
                source_name=name,
                raw_json=item,
            )


# ============================================================
# Weapon Entity Import
# ============================================================


def import_weapon_entity(
    db,
    record,
):
    """
    Import ESO-Hub weapon skill-line information
    as canonical entities.

    Example:

        One Hand and Shield
        Destruction Staff
        Two Handed
    """

    weapon = record.get(
        "weapon"
    )

    if not weapon:
        return

    if isinstance(
        weapon,
        dict,
    ):

        weapons = [
            weapon
        ]

    elif isinstance(
        weapon,
        list,
    ):

        weapons = weapon

    else:

        return

    for item in weapons:

        if not isinstance(
            item,
            dict,
        ):
            continue

        skill_line = item.get(
            "skill_line"
        )

        if not isinstance(
            skill_line,
            str,
        ):
            continue

        skill_line = skill_line.strip()

        if not skill_line:
            continue

        entity_id = ensure_entity(
            db,
            "weapon_skill_line",
            skill_line,
        )

        source_id = item.get(
            "skill_line_url"
        )

        ensure_source_mapping(
            db=db,
            entity_id=entity_id,
            source="ESO-Hub",
            source_entity_type="weapon_skill_line",
            source_id=source_id,
            source_name=skill_line,
            raw_json=item,
        )


# ============================================================
# Main
# ============================================================


def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Canonical Entity Importer")
    print("=" * 60)

    print()
    print(
        f"Source: {SOURCE_PATH}"
    )

    print(
        f"Database: {DB_PATH}"
    )

    print()

    if not SOURCE_PATH.exists():

        raise FileNotFoundError(
            f"Source file not found:\n"
            f"{SOURCE_PATH}"
        )

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found:\n"
            f"{DB_PATH}"
        )

    # --------------------------------------------------------
    # Load source
    # --------------------------------------------------------

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(
            handle
        )

    # ESO-Hub crawler output is an object containing
    # metadata plus the actual skill list.

    if isinstance(
        data,
        dict,
    ):

        if "skills" not in data:

            raise ValueError(
                "ESO-Hub source does not contain "
                "a 'skills' list."
            )

        data = data["skills"]

    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "ESO-Hub source must contain "
            "a JSON list of records."
        )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    db = sqlite3.connect(
        DB_PATH
    )

    try:

        db.execute(
            "PRAGMA foreign_keys = ON"
        )

        skill_count = 0
        relationship_changes = 0
        weapon_changes = 0

        # ----------------------------------------------------
        # Import
        # ----------------------------------------------------

        for record in data:

            if not isinstance(
                record,
                dict,
            ):
                continue

            if import_skill_entity(
                db,
                record,
            ):

                skill_count += 1

            before = db.total_changes

            import_relationship_entities(
                db,
                record,
            )

            relationship_changes += (
                db.total_changes
                - before
            )

            before = db.total_changes

            import_weapon_entity(
                db,
                record,
            )

            weapon_changes += (
                db.total_changes
                - before
            )

        db.commit()

        # ----------------------------------------------------
        # Counts
        # ----------------------------------------------------

        entity_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity
            """
        ).fetchone()[0]

        source_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity_source
            """
        ).fetchone()[0]

        skill_entity_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity
            WHERE entity_type = 'skill'
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        print("=" * 60)
        print(" IMPORT COMPLETE")
        print("=" * 60)

        print()

        print(
            f"Skill records processed: "
            f"{skill_count}"
        )

        print(
            f"Relationship changes:     "
            f"{relationship_changes}"
        )

        print(
            f"Weapon changes:           "
            f"{weapon_changes}"
        )

        print()

        print(
            f"Canonical skill entities: "
            f"{skill_entity_count}"
        )

        print(
            f"Canonical entities:       "
            f"{entity_count}"
        )

        print(
            f"Source mappings:          "
            f"{source_count}"
        )

        print()

        print("=" * 60)

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()