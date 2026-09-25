from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.build_service import BuildService


@dataclass(frozen=True)
class TeamDeletionResult:
    team_name: str
    removed_memberships: int
    removed_build_assignments: int


def _text(value: object) -> str:
    return str(value or "").strip()


def delete_team_everywhere(roster_service, build_service: BuildService, team_name: str) -> TeamDeletionResult:
    """Delete one team without deleting people, characters, builds, or raid-plan history."""
    name = _text(team_name)
    if not name:
        raise ValueError("team name is required")

    team_row = roster_service.db.execute(
        "SELECT id, name FROM team WHERE name = ? COLLATE NOCASE",
        (name,),
    ).fetchone()
    if team_row is None:
        raise ValueError(f"Team does not exist: {name}")

    canonical_name = str(team_row["name"])
    team_id = int(team_row["id"])
    membership_row = roster_service.db.execute(
        "SELECT COUNT(*) AS count FROM team_member WHERE team_id = ?",
        (team_id,),
    ).fetchone()
    removed_memberships = int(membership_row["count"] if membership_row else 0)

    catalog_service = build_service.canonical.catalog_service
    catalog_path = Path(catalog_service.catalog_path)
    catalog_existed = catalog_path.exists()
    catalog_backup = catalog_path.read_text(encoding="utf-8") if catalog_existed else ""
    catalog = catalog_service.load_strict()
    team_key = canonical_name.casefold()
    assignments = [
        row
        for row in catalog.get("team_assignments", [])
        if isinstance(row, dict)
    ]
    removed_build_assignments = sum(
        1 for row in assignments
        if _text(row.get("team_name")).casefold() == team_key
    )
    updated_catalog = dict(catalog)
    updated_catalog["team_assignments"] = [
        row
        for row in assignments
        if _text(row.get("team_name")).casefold() != team_key
    ]

    connection = roster_service.db.connection
    connection.execute("SAVEPOINT bff_team_delete")
    try:
        if removed_build_assignments:
            catalog_service.save(updated_catalog)
        connection.execute("DELETE FROM team_member WHERE team_id = ?", (team_id,))
        connection.execute("DELETE FROM team WHERE id = ?", (team_id,))
        connection.execute("RELEASE SAVEPOINT bff_team_delete")
    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT bff_team_delete")
        connection.execute("RELEASE SAVEPOINT bff_team_delete")
        if catalog_existed:
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(catalog_backup, encoding="utf-8")
        elif catalog_path.exists():
            catalog_path.unlink()
        raise

    return TeamDeletionResult(
        team_name=canonical_name,
        removed_memberships=removed_memberships,
        removed_build_assignments=removed_build_assignments,
    )


__all__ = ["TeamDeletionResult", "delete_team_everywhere"]
