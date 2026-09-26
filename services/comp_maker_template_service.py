from __future__ import annotations

"""User-owned reusable planning templates for Comp Maker.

Comp Maker Templates are intentionally allowed to be incomplete. They preserve only
composition-relevant planning evidence and never own player, character, Raid Plan, or
readiness identity.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from engine.config import get_user_database_path
from models.build_model import PlayerBuild
from services.eso_database import EsoDatabase
from services.team_prescription_slot_constraints import build_gear_set_names
from services.planning_artifact_pydantic_schema import validate_comp_maker_template


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _unique(values) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return tuple(result)


@dataclass(frozen=True)
class CompMakerTemplate:
    template_id: str
    name: str
    role: str = ""
    eso_class: str = ""
    gear_sets: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mundus: str = ""
    notes: str = ""
    source_build_id: str = ""
    source_plan_name: str = ""
    source_seat_id: str = ""


class CompMakerTemplateService:
    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path or get_user_database_path())
        self.db = EsoDatabase(self.database_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS comp_maker_template (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                eso_class TEXT NOT NULL DEFAULT '',
                gear_sets_json TEXT NOT NULL DEFAULT '[]',
                skills_json TEXT NOT NULL DEFAULT '[]',
                mundus TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                source_build_id TEXT NOT NULL DEFAULT '',
                source_plan_name TEXT NOT NULL DEFAULT '',
                source_seat_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.db.commit()

    @staticmethod
    def _stable_id(name: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"bff:comp-maker-template:{_clean(name).casefold()}"))

    @staticmethod
    def from_comp_build(build: PlayerBuild, *, name: str | None = None) -> CompMakerTemplate:
        if _clean(getattr(build, "BuildKind", "")).casefold() != "comp":
            raise ValueError("Comp Maker Templates can only be created from Comp Builds.")

        planned_gear = _unique(getattr(build, "PlannedGearSets", ()) or ())
        gear_sets = planned_gear or _unique(build_gear_set_names(build))

        planned_skills = _unique(getattr(build, "PlannedSkills", ()) or ())
        if planned_skills:
            skills = planned_skills
        else:
            skills = _unique(
                [
                    *(getattr(build, "FrontBarSkills", ()) or ()),
                    *(getattr(build, "BackBarSkills", ()) or ()),
                ]
            )

        template_name = _clean(name) or _clean(getattr(build, "BuildName", "")) or "Comp Maker Template"
        return CompMakerTemplate(
            template_id=CompMakerTemplateService._stable_id(template_name),
            name=template_name,
            role=_clean(getattr(build, "Role", "")),
            eso_class=_clean(getattr(build, "EsoClass", "")),
            gear_sets=gear_sets,
            skills=skills,
            mundus=_clean(getattr(build, "Mundus", "")),
            notes=_clean(getattr(build, "Notes", "")),
            source_build_id=_clean(getattr(build, "BuildId", "")),
            source_plan_name=_clean(getattr(build, "SourcePlanName", "")),
            source_seat_id=_clean(getattr(build, "SourceSeatId", "")),
        )

    def save(self, template: CompMakerTemplate) -> CompMakerTemplate:
        payload = validate_comp_maker_template({
            "template_id": template.template_id,
            "name": template.name,
            "role": template.role,
            "eso_class": template.eso_class,
            "gear_sets": tuple(template.gear_sets),
            "skills": tuple(template.skills),
            "mundus": template.mundus,
            "notes": template.notes,
            "source_build_id": template.source_build_id,
            "source_plan_name": template.source_plan_name,
            "source_seat_id": template.source_seat_id,
        })
        db = self.db.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            existing = db.execute(
                "SELECT created_at FROM comp_maker_template WHERE template_id = ?",
                (payload["template_id"],),
            ).fetchone()
            created_at = str(existing["created_at"]) if existing is not None else now
            db.execute(
                """
                INSERT INTO comp_maker_template (
                    template_id, name, role, eso_class, gear_sets_json, skills_json,
                    mundus, notes, source_build_id, source_plan_name, source_seat_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    eso_class = excluded.eso_class,
                    gear_sets_json = excluded.gear_sets_json,
                    skills_json = excluded.skills_json,
                    mundus = excluded.mundus,
                    notes = excluded.notes,
                    source_build_id = excluded.source_build_id,
                    source_plan_name = excluded.source_plan_name,
                    source_seat_id = excluded.source_seat_id,
                    updated_at = excluded.updated_at
                """,
                (
                    payload["template_id"], payload["name"], payload["role"],
                    payload["eso_class"], json.dumps(list(payload["gear_sets"]), ensure_ascii=False),
                    json.dumps(list(payload["skills"]), ensure_ascii=False), payload["mundus"],
                    payload["notes"], payload["source_build_id"], payload["source_plan_name"],
                    payload["source_seat_id"], created_at, now,
                ),
            )
            row = db.execute(
                """SELECT template_id, name, role, eso_class, gear_sets_json, skills_json,
                          mundus, notes, source_build_id, source_plan_name, source_seat_id
                   FROM comp_maker_template WHERE template_id = ?""",
                (payload["template_id"],),
            ).fetchone()
            if row is None:
                raise RuntimeError("Comp Maker Template was not persisted")
            read_back = validate_comp_maker_template({
                "template_id": str(row["template_id"]), "name": str(row["name"]),
                "role": str(row["role"]), "eso_class": str(row["eso_class"]),
                "gear_sets": tuple(json.loads(str(row["gear_sets_json"]))),
                "skills": tuple(json.loads(str(row["skills_json"]))),
                "mundus": str(row["mundus"]), "notes": str(row["notes"]),
                "source_build_id": str(row["source_build_id"]),
                "source_plan_name": str(row["source_plan_name"]),
                "source_seat_id": str(row["source_seat_id"]),
            })
            if read_back != payload:
                raise RuntimeError("Comp Maker Template did not round-trip exactly")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return template

    def save_from_comp_build(self, build: PlayerBuild, *, name: str | None = None) -> CompMakerTemplate:
        return self.save(self.from_comp_build(build, name=name))

    def list_templates(self) -> tuple[CompMakerTemplate, ...]:
        rows = self.db.execute(
            """
            SELECT template_id, name, role, eso_class, gear_sets_json, skills_json,
                   mundus, notes, source_build_id, source_plan_name, source_seat_id
            FROM comp_maker_template
            ORDER BY name COLLATE NOCASE, template_id
            """
        ).fetchall()
        result: list[CompMakerTemplate] = []
        for row in rows:
            try:
                gear_sets = _unique(json.loads(str(row["gear_sets_json"] or "[]")))
            except (TypeError, ValueError, json.JSONDecodeError):
                gear_sets = ()
            try:
                skills = _unique(json.loads(str(row["skills_json"] or "[]")))
            except (TypeError, ValueError, json.JSONDecodeError):
                skills = ()
            result.append(
                CompMakerTemplate(
                    template_id=str(row["template_id"] or ""),
                    name=str(row["name"] or ""),
                    role=str(row["role"] or ""),
                    eso_class=str(row["eso_class"] or ""),
                    gear_sets=gear_sets,
                    skills=skills,
                    mundus=str(row["mundus"] or ""),
                    notes=str(row["notes"] or ""),
                    source_build_id=str(row["source_build_id"] or ""),
                    source_plan_name=str(row["source_plan_name"] or ""),
                    source_seat_id=str(row["source_seat_id"] or ""),
                )
            )
        return tuple(result)


__all__ = ["CompMakerTemplate", "CompMakerTemplateService"]
