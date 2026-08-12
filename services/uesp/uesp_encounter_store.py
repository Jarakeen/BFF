from __future__ import annotations

"""SQLite persistence for the UESP encounter/content knowledge layer."""

import sqlite3
from dataclasses import asdict
from typing import Any

from models.uesp_models import UespBoss, UespContent
from services.encounter_schema import ensure_encounter_schema


class UespEncounterStore:
    """Writes parsed UESP encounter facts into the existing ESO database.

    This store deliberately does not replace the existing JSON UESP store.
    JSON remains useful as the raw/cache representation; this class creates
    the relational representation used by FoundryDock's analysis layer.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        ensure_encounter_schema(self.connection)

    def save_content(self, content: UespContent) -> None:
        source = content.source
        self.connection.execute(
            """
            INSERT INTO content (
                id, name, slug, content_type, summary, location,
                source_url, source_page_title, source_revision_id,
                retrieved_at, source_license
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                slug=excluded.slug,
                content_type=excluded.content_type,
                summary=excluded.summary,
                location=excluded.location,
                source_url=excluded.source_url,
                source_page_title=excluded.source_page_title,
                source_revision_id=excluded.source_revision_id,
                retrieved_at=excluded.retrieved_at,
                source_license=excluded.source_license
            """,
            (
                content.id,
                content.name,
                content.id,
                content.content_type,
                content.summary,
                content.location,
                source.url if source else None,
                source.page_title if source else None,
                str(source.revision_id) if source and source.revision_id is not None else None,
                source.retrieved_at if source else None,
                source.license if source else None,
            ),
        )
        self.connection.commit()

        for achievement in content.achievements:
            self._save_content_section(content.id, "achievements", [asdict(a) for a in content.achievements])
            break

    def save_boss(self, boss: UespBoss) -> None:
        if not boss.content_id:
            raise ValueError(f"Boss '{boss.name}' has no content_id")

        self._ensure_content_stub(boss)
        source = boss.source

        self.connection.execute(
            """
            INSERT INTO encounter (
                id, content_id, name, slug, summary, location, species, reaction,
                source_url, source_page_title, source_revision_id,
                retrieved_at, source_license
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                content_id=excluded.content_id,
                name=excluded.name,
                slug=excluded.slug,
                summary=excluded.summary,
                location=excluded.location,
                species=excluded.species,
                reaction=excluded.reaction,
                source_url=excluded.source_url,
                source_page_title=excluded.source_page_title,
                source_revision_id=excluded.source_revision_id,
                retrieved_at=excluded.retrieved_at,
                source_license=excluded.source_license
            """,
            (
                boss.id,
                boss.content_id,
                boss.name,
                boss.id,
                boss.summary,
                boss.location,
                boss.species,
                boss.reaction,
                source.url if source else None,
                source.page_title if source else None,
                str(source.revision_id) if source and source.revision_id is not None else None,
                source.retrieved_at if source else None,
                source.license if source else None,
            ),
        )

        self.connection.execute(
            """
            INSERT INTO encounter_health(encounter_id, normal, veteran, hardmode)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(encounter_id) DO UPDATE SET
                normal=excluded.normal,
                veteran=excluded.veteran,
                hardmode=excluded.hardmode
            """,
            (boss.id, boss.health.normal, boss.health.veteran, boss.health.hardmode),
        )

        self._replace_abilities(boss)
        self._replace_mechanics(boss)
        self._replace_phases(boss)
        self._replace_dialogue(boss)
        self._save_boss_sections(boss)
        self.connection.commit()

    def _ensure_content_stub(self, boss: UespBoss) -> None:
        self.connection.execute(
            """
            INSERT INTO content(id, name, slug, content_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name
            """,
            (
                boss.content_id,
                boss.content_name or boss.content_id.replace("_", " ").title(),
                boss.content_id,
                "unknown",
            ),
        )

    def _replace_abilities(self, boss: UespBoss) -> None:
        self.connection.execute("DELETE FROM encounter_ability WHERE encounter_id = ?", (boss.id,))
        for ability in boss.abilities:
            self.connection.execute(
                """
                INSERT INTO encounter_ability(
                    encounter_id, name, description, source_section,
                    source_url, source_revision_id, interruptible, interrupt_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    boss.id,
                    ability.name,
                    ability.description,
                    "Skills and Abilities",
                    boss.source.url if boss.source else None,
                    str(boss.source.revision_id) if boss.source and boss.source.revision_id is not None else None,
                    None,
                    "",
                ),
            )

    def _replace_mechanics(self, boss: UespBoss) -> None:
        self.connection.execute("DELETE FROM encounter_mechanic WHERE encounter_id = ?", (boss.id,))
        for mechanic in boss.mechanics:
            self.connection.execute(
                """
                INSERT INTO encounter_mechanic(
                    encounter_id, name, description, interpretation_status,
                    source_section, source_url, source_revision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    boss.id,
                    self._mechanic_name(mechanic),
                    mechanic.description,
                    "unclassified",
                    "Skills and Abilities",
                    boss.source.url if boss.source else None,
                    str(boss.source.revision_id) if boss.source and boss.source.revision_id is not None else None,
                ),
            )

    def _replace_phases(self, boss: UespBoss) -> None:
        self.connection.execute("DELETE FROM encounter_phase WHERE encounter_id = ?", (boss.id,))
        for phase in boss.phases:
            self.connection.execute(
                """
                INSERT INTO encounter_phase(
                    encounter_id, label, threshold, description,
                    source_section, source_url, source_revision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    boss.id,
                    phase.label,
                    phase.threshold,
                    phase.description,
                    "Phases",
                    boss.source.url if boss.source else None,
                    str(boss.source.revision_id) if boss.source and boss.source.revision_id is not None else None,
                ),
            )

    def _replace_dialogue(self, boss: UespBoss) -> None:
        self.connection.execute("DELETE FROM encounter_dialogue WHERE encounter_id = ?", (boss.id,))

        ability_ids = {
            row["name"]: row["id"]
            for row in self.connection.execute(
                "SELECT id, name FROM encounter_ability WHERE encounter_id = ?", (boss.id,)
            )
        }

        for line in boss.dialogue:
            matched_id = ability_ids.get(line.ability or "")
            self.connection.execute(
                """
                INSERT INTO encounter_dialogue(
                    encounter_id, trigger, speaker, line, matched_ability_id,
                    source_section, source_url, source_revision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    boss.id,
                    line.trigger or "Unspecified",
                    line.speaker,
                    line.line,
                    matched_id,
                    "Dialogue",
                    boss.source.url if boss.source else None,
                    str(boss.source.revision_id) if boss.source and boss.source.revision_id is not None else None,
                ),
            )

    def _save_boss_sections(self, boss: UespBoss) -> None:
        import json

        source_url = boss.source.url if boss.source else None
        revision = str(boss.source.revision_id) if boss.source and boss.source.revision_id is not None else None
        sections: dict[str, Any] = {
            "difficulty_notes": asdict(boss.difficulty_notes),
            "notes": boss.notes,
            "strategy_notes": boss.strategy_notes,
            "related_npcs": boss.related_npcs,
            "related_quests": boss.related_quests,
        }
        for name, payload in sections.items():
            self.connection.execute(
                """
                INSERT INTO encounter_section(
                    encounter_id, section_name, payload_json, source_url, source_revision_id
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(encounter_id, section_name) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    source_url=excluded.source_url,
                    source_revision_id=excluded.source_revision_id
                """,
                (boss.id, name, json.dumps(payload, ensure_ascii=False), source_url, revision),
            )

    @staticmethod
    def _mechanic_name(mechanic: Any) -> str:
        # Current UespMechanic does not carry a separate name. Until the model
        # does, use a stable generated label rather than pretending the
        # description itself is a canonical ability name.
        text = mechanic.description.strip()
        return text[:120] if text else "Unspecified mechanic"

    def _save_content_section(self, content_id: str, section_name: str, payload: Any) -> None:
        import json
        self.connection.execute(
            """
            INSERT INTO content_section(content_id, section_name, payload_json)
            VALUES (?, ?, ?)
            ON CONFLICT(content_id, section_name) DO UPDATE SET payload_json=excluded.payload_json
            """,
            (content_id, section_name, json.dumps(payload, ensure_ascii=False)),
        )
