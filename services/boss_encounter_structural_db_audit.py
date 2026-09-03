from __future__ import annotations

"""Audit persisted boss structural rows against the canonical UESP boss corpus."""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from services.boss_encounter_structural_import import (
    UNRESOLVED_ABILITY_NAME,
    _dialogue_rows,
    _load_source,
    _phase_rows,
    _prepared_ability_rows,
    _source_meta,
)


@dataclass(frozen=True)
class BossStructuralDatabaseAudit:
    bosses: int
    expected_health: int
    matched_health: int
    expected_abilities: int
    matched_abilities: int
    expected_phases: int
    matched_phases: int
    expected_dialogue: int
    matched_dialogue: int
    expected_sections: int
    matched_sections: int
    problems: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.problems)


def _compare_rows(
    label: str,
    encounter_id: str,
    expected: list[tuple],
    actual: list[tuple],
    problems: list[str],
) -> int:
    remaining = list(actual)
    matched = 0
    for row in expected:
        try:
            index = remaining.index(row)
        except ValueError:
            problems.append(f"{encounter_id}: missing/conflicting {label} row {row!r}")
        else:
            matched += 1
            remaining.pop(index)
    for row in remaining:
        problems.append(f"{encounter_id}: unexpected {label} row {row!r}")
    return matched


def audit_boss_structural_database(
    connection: sqlite3.Connection,
    source_dir: Path,
) -> BossStructuralDatabaseAudit:
    problems: list[str] = []
    bosses = 0
    expected_health = matched_health = 0
    expected_abilities = matched_abilities = 0
    expected_phases = matched_phases = 0
    expected_dialogue = matched_dialogue = 0
    expected_sections = matched_sections = 0

    for path in sorted(Path(source_dir).glob("*.json")):
        payload = _load_source(path)
        encounter_id = str(payload["id"]).strip()
        source_url, revision = _source_meta(payload)
        bosses += 1

        health = payload.get("health") if isinstance(payload.get("health"), dict) else {}
        expected_health_rows = [(
            str(health.get("normal") or ""),
            str(health.get("veteran") or ""),
            str(health.get("hardmode") or ""),
        )]
        actual_health_rows = [
            tuple(str(value or "") for value in row)
            for row in connection.execute(
                "SELECT normal, veteran, hardmode FROM encounter_health WHERE encounter_id=?",
                (encounter_id,),
            ).fetchall()
        ]
        expected_health += 1
        matched_health += _compare_rows(
            "health", encounter_id, expected_health_rows, actual_health_rows, problems
        )

        expected_ability_rows = [
            (
                storage_name,
                str(row.get("description") or ""),
                "Skills and Abilities",
                source_url,
                revision,
            )
            for row, storage_name in _prepared_ability_rows(payload)
        ]
        actual_ability_rows = [
            tuple(str(value or "") for value in row)
            for row in connection.execute(
                """SELECT name, description, source_section, source_url, source_revision_id
                   FROM encounter_ability WHERE encounter_id=?""",
                (encounter_id,),
            ).fetchall()
        ]
        expected_abilities += len(expected_ability_rows)
        matched_abilities += _compare_rows(
            "ability", encounter_id, expected_ability_rows, actual_ability_rows, problems
        )

        expected_phase_rows: list[tuple] = []
        for index, raw in enumerate(_phase_rows(payload), start=1):
            if isinstance(raw, dict):
                label = str(raw.get("label") or raw.get("name") or raw.get("phase") or "")
                threshold = str(raw.get("threshold") or "")
                description = str(raw.get("description") or "")
            else:
                label = f"Phase {index}"
                threshold = ""
                description = str(raw or "")
            expected_phase_rows.append(
                (label, threshold, description, "Phases", source_url, revision)
            )
        actual_phase_rows = [
            tuple(str(value or "") for value in row)
            for row in connection.execute(
                """SELECT label, threshold, description, source_section, source_url, source_revision_id
                   FROM encounter_phase WHERE encounter_id=?""",
                (encounter_id,),
            ).fetchall()
        ]
        expected_phases += len(expected_phase_rows)
        matched_phases += _compare_rows(
            "phase", encounter_id, expected_phase_rows, actual_phase_rows, problems
        )

        raw_name_counts: dict[str, int] = {}
        for row, _storage_name in _prepared_ability_rows(payload):
            raw_name = str(row.get("name") or "").strip()
            raw_name_counts[raw_name] = raw_name_counts.get(raw_name, 0) + 1
        expected_dialogue_rows = []
        for row in _dialogue_rows(payload):
            line = str(row.get("line") or "").strip()
            if not line:
                continue
            ability = str(row.get("ability") or "").strip()
            matched_name = ability if ability and raw_name_counts.get(ability, 0) == 1 else ""
            expected_dialogue_rows.append((
                str(row.get("trigger") or "Unspecified"),
                str(row.get("speaker") or ""),
                line,
                matched_name,
                "Dialogue",
                source_url,
                revision,
            ))
        actual_dialogue_rows = [
            tuple(str(value or "") for value in row)
            for row in connection.execute(
                """SELECT d.trigger, d.speaker, d.line, COALESCE(a.name, ''),
                          d.source_section, d.source_url, d.source_revision_id
                   FROM encounter_dialogue d
                   LEFT JOIN encounter_ability a ON a.id=d.matched_ability_id
                   WHERE d.encounter_id=?""",
                (encounter_id,),
            ).fetchall()
        ]
        expected_dialogue += len(expected_dialogue_rows)
        matched_dialogue += _compare_rows(
            "dialogue", encounter_id, expected_dialogue_rows, actual_dialogue_rows, problems
        )

        sections = {
            "difficulty_notes": payload.get("difficulty_notes") or {},
            "notes": payload.get("notes") or [],
            "strategy_notes": payload.get("strategy_notes") or [],
            "related_npcs": payload.get("related_npcs") or [],
            "related_quests": payload.get("related_quests") or [],
        }
        expected_section_rows = [
            (
                name,
                json.dumps(value, ensure_ascii=False, sort_keys=True),
                source_url,
                revision,
            )
            for name, value in sections.items()
        ]
        actual_section_rows = [
            tuple(str(value or "") for value in row)
            for row in connection.execute(
                """SELECT section_name, payload_json, source_url, source_revision_id
                   FROM encounter_section WHERE encounter_id=?""",
                (encounter_id,),
            ).fetchall()
        ]
        expected_sections += len(expected_section_rows)
        matched_sections += _compare_rows(
            "section", encounter_id, expected_section_rows, actual_section_rows, problems
        )

    return BossStructuralDatabaseAudit(
        bosses=bosses,
        expected_health=expected_health,
        matched_health=matched_health,
        expected_abilities=expected_abilities,
        matched_abilities=matched_abilities,
        expected_phases=expected_phases,
        matched_phases=matched_phases,
        expected_dialogue=expected_dialogue,
        matched_dialogue=matched_dialogue,
        expected_sections=expected_sections,
        matched_sections=matched_sections,
        problems=tuple(problems),
    )
