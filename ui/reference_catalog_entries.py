from __future__ import annotations

"""Reference-page projections for canonical player-facing ESO catalog data.

This module is intentionally presentation-only. It reads the existing canonical
ESO SQLite data and turns gear sets, active skills, passives, and Champion Points
into ``ReferenceEntry`` rows. Nothing here is consumed by combat math or runtime
mechanics.
"""

from pathlib import Path

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from ui.reference_data_model import ReferenceEntry


def _clean(value) -> str:
    return str(value or "").strip()


def _detail(label: str, value) -> tuple[str, str] | None:
    text = _clean(value)
    return (label, text) if text else None


def _open_database(database_path: Path | None = None) -> EsoDatabase:
    return EsoDatabase(Path(database_path or (get_data_dir() / "eso.db")))


def build_gear_set_reference_entries(
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    database = _open_database(database_path)
    try:
        if not database.table_exists("gear_set"):
            return ()

        bonus_exists = database.table_exists("gear_set_bonus")
        if bonus_exists:
            rows = database.execute(
                """
                SELECT
                    gs.id,
                    gs.name,
                    gs.category,
                    gs.max_equip_count,
                    gsb.piece_count,
                    gsb.description
                FROM gear_set gs
                LEFT JOIN gear_set_bonus gsb ON gsb.set_id = gs.id
                WHERE gs.name IS NOT NULL AND TRIM(gs.name) <> ''
                ORDER BY gs.name COLLATE NOCASE, gsb.piece_count
                """
            ).fetchall()
        else:
            rows = database.execute(
                """
                SELECT id, name, category, max_equip_count,
                       NULL AS piece_count, NULL AS description
                FROM gear_set
                WHERE name IS NOT NULL AND TRIM(name) <> ''
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

        grouped: dict[int, dict] = {}
        for row in rows:
            set_id = int(row["id"])
            bucket = grouped.setdefault(
                set_id,
                {
                    "name": _clean(row["name"]),
                    "category": _clean(row["category"]),
                    "max_equip_count": row["max_equip_count"],
                    "bonuses": [],
                },
            )
            if row["piece_count"] is not None and _clean(row["description"]):
                bucket["bonuses"].append(
                    (int(row["piece_count"]), _clean(row["description"]))
                )

        entries: list[ReferenceEntry] = []
        for set_id, row in grouped.items():
            bonuses = tuple(row["bonuses"])
            summary = (
                bonuses[-1][1]
                if bonuses
                else "Canonical gear-set record. No set-bonus description is currently stored."
            )
            details: list[tuple[str, str]] = [
                ("Authority", "Canonical gear-set data"),
                ("Set ID", str(set_id)),
            ]
            if row["category"]:
                details.append(("Category", row["category"]))
            if row["max_equip_count"] is not None:
                details.append(("Maximum equipped", str(row["max_equip_count"])))
            details.extend(
                (f"{piece_count}-piece bonus", description)
                for piece_count, description in bonuses
            )
            tags = ["GEAR SET"]
            if row["category"]:
                tags.append(row["category"].upper())

            entries.append(
                ReferenceEntry(
                    name=row["name"],
                    entry_type="Gear Set",
                    source_scope="Gear",
                    tags=tuple(tags),
                    summary=summary,
                    details=tuple(details),
                    related=(),
                    field_note=(
                        "Current canonical values only. Historical set changes, when reviewed, "
                        "are presentation trivia and never feed combat calculations."
                    ),
                    used_by=("Builds", "Comp Maker", "Extreme Builder", "Rotation Builder"),
                    evidence=(f"Canonical gear set: {set_id}",),
                )
            )
        return tuple(entries)
    except Exception:
        return ()
    finally:
        database.close()


def _skill_entry(row: dict) -> ReferenceEntry | None:
    name = _clean(row.get("name"))
    if not name:
        return None

    skill_line = _clean(row.get("skill_line"))
    display_name = f"{name} — {skill_line}" if skill_line else name
    is_passive = bool(row.get("is_passive"))
    entry_type = "Passive" if is_passive else "Skill"
    source_scope = "Skills"
    summary = _clean(row.get("description")) or (
        "Canonical skill record. No current tooltip description is stored."
    )

    details: list[tuple[str, str]] = [
        ("Authority", "Canonical skill data"),
        ("Skill ID", _clean(row.get("id")) or "Not recorded"),
        ("Current name", name),
    ]
    for item in (
        _detail("Skill line", skill_line),
        _detail("Class", row.get("class_type")),
        _detail("Skill type", row.get("skill_type")),
        _detail("Target", row.get("target")),
        _detail("Resource", row.get("base_mechanic")),
        _detail("Cost", row.get("cost")),
        _detail("Buff type", row.get("buff_type")),
    ):
        if item is not None:
            details.append(item)

    morph = row.get("morph")
    if morph is not None:
        details.append(("Morph", str(morph)))
    rank = row.get("rank")
    if rank is not None:
        details.append(("Rank", str(rank)))
    ability_id = row.get("ability_id")
    if ability_id is not None:
        details.append(("Ability ID", str(ability_id)))

    related = tuple(
        dict.fromkeys(
            value
            for value in (
                skill_line,
                _clean(row.get("class_type")),
            )
            if value
        )
    )
    tags = [entry_type.upper()]
    if row.get("is_crafted"):
        tags.append("SCRIBING")
    if _clean(row.get("class_type")):
        tags.append(_clean(row.get("class_type")).upper())

    return ReferenceEntry(
        name=display_name,
        entry_type=entry_type,
        source_scope=source_scope,
        tags=tuple(tags),
        summary=summary,
        details=tuple(details),
        related=related,
        field_note=(
            "Current canonical skill data. Historical balance and wording changes are "
            "Reference-page trivia only and never replace current mechanics values."
        ),
        used_by=("Builds", "Rotation Builder", "Extreme Builder", "Performance / Raid Review"),
        evidence=(f"Canonical skill: {_clean(row.get('id')) or name}",),
    )


def build_skill_reference_entries(
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    database = _open_database(database_path)
    try:
        service = ReferenceDataService(database)
        entries = []
        seen: set[tuple[str, str]] = set()
        for row in service.list_skills():
            entry = _skill_entry(row)
            if entry is None:
                continue
            key = (entry.entry_type.casefold(), entry.name.casefold())
            if key in seen:
                continue
            seen.add(key)
            entries.append(entry)
        return tuple(entries)
    finally:
        database.close()


def build_champion_point_reference_entries(
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    database = _open_database(database_path)
    try:
        service = ReferenceDataService(database)
        entries: list[ReferenceEntry] = []
        for row in service.list_champion_points():
            name = _clean(row.get("name"))
            if not name:
                continue
            description = _clean(row.get("description"))
            min_description = _clean(row.get("min_description"))
            max_description = _clean(row.get("max_description"))
            summary = description or max_description or min_description or (
                "Canonical Champion Point record. No current description is stored."
            )
            details: list[tuple[str, str]] = [
                ("Authority", "Canonical Champion Point data"),
                ("Champion Point ID", _clean(row.get("id")) or "Not recorded"),
            ]
            for item in (
                _detail("Discipline", row.get("discipline_id")),
                _detail("Skill type", row.get("skill_type")),
                _detail("Minimum description", min_description),
                _detail("Maximum description", max_description),
                _detail("Maximum points", row.get("max_points")),
                _detail("Jump points", row.get("jump_points")),
            ):
                if item is not None:
                    details.append(item)
            entries.append(
                ReferenceEntry(
                    name=name,
                    entry_type="Champion Point",
                    source_scope="Champion Points",
                    tags=("CHAMPION POINT",),
                    summary=summary,
                    details=tuple(details),
                    field_note=(
                        "Current canonical Champion Point data. Historical CP-system changes are "
                        "presentation trivia only."
                    ),
                    used_by=("Builds", "Extreme Builder"),
                    evidence=(f"Canonical Champion Point: {_clean(row.get('id')) or name}",),
                )
            )
        return tuple(entries)
    finally:
        database.close()


def build_player_catalog_reference_entries(
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Return canonical gear/skill/passive/CP entries for the Reference page."""

    return (
        *build_gear_set_reference_entries(database_path),
        *build_skill_reference_entries(database_path),
        *build_champion_point_reference_entries(database_path),
    )
