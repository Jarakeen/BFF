import json
from pathlib import Path

from ui.reference_encounter_evidence import load_unbacked_encounter_evidence_entries


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _boss(root: Path, boss_id: str, name: str) -> None:
    _write(
        root / "eso_info" / "bosses" / f"{boss_id}.json",
        {
            "id": boss_id,
            "name": name,
            "content_id": "dreadsail_reef",
            "content_name": "Dreadsail Reef",
            "mechanics": [],
            "phases": [],
            "source": {},
        },
    )


def _packet(root: Path, filename: str, encounter_id: str, encounter_name: str, evidence: list[dict]) -> None:
    _write(
        root / "encounter_evidence" / filename,
        {
            "schema_version": 1,
            "content_id": "dreadsail_reef",
            "encounter_id": encounter_id,
            "encounter_name": encounter_name,
            "evidence": evidence,
        },
    )


def test_unbacked_paired_encounter_projects_named_reviewed_mechanics(tmp_path):
    _boss(tmp_path, "lylanar", "Lylanar")
    _boss(tmp_path, "turlassil", "Turlassil")
    _packet(
        tmp_path,
        "boss1.json",
        "lylanar_turlassil",
        "Lylanar and Turlassil",
        [
            {
                "fact_type": "mechanic",
                "fact_key": "firebrand",
                "value": {"name": "Firebrand", "element": "fire"},
                "source_type": "combat_addon",
                "source_name": "Combat Alerts",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic",
                "fact_key": "firebrand",
                "value": {"name": "Firebrand", "element": "fire"},
                "source_type": "guide",
                "source_name": "Reviewed DSR Guide",
                "confidence": "high",
            },
        ],
    )

    entries = load_unbacked_encounter_evidence_entries(tmp_path)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.name == "Firebrand — Lylanar and Turlassil"
    assert entry.entry_type == "Mechanic Evidence"
    assert "Corroborated" in entry.detail_text()
    assert "Element: fire" in entry.detail_text()
    assert "not yet canonical encounter truth" in entry.detail_text()
    assert len(entry.evidence) == 2


def test_boss_backed_encounter_packet_is_not_duplicated(tmp_path):
    _boss(tmp_path, "reef_guardian", "Reef Guardian")
    _packet(
        tmp_path,
        "boss2.json",
        "reef_guardian",
        "Reef Guardian",
        [
            {
                "fact_type": "mechanic",
                "fact_key": "acid_reflux",
                "value": {"name": "Acid Reflux", "damage_type": "poison"},
                "source_type": "guide",
                "source_name": "Reviewed DSR Guide",
                "confidence": "high",
            }
        ],
    )

    assert load_unbacked_encounter_evidence_entries(tmp_path) == ()


def test_conflicting_unbacked_mechanic_evidence_is_not_rendered(tmp_path):
    _packet(
        tmp_path,
        "pair.json",
        "paired_encounter",
        "Paired Encounter",
        [
            {
                "fact_type": "mechanic",
                "fact_key": "test_mechanic",
                "value": {"name": "Test Mechanic", "element": "fire"},
                "source_type": "guide",
                "source_name": "Guide A",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic",
                "fact_key": "test_mechanic",
                "value": {"name": "Test Mechanic", "element": "ice"},
                "source_type": "guide",
                "source_name": "Guide B",
                "confidence": "high",
            },
        ],
    )

    assert load_unbacked_encounter_evidence_entries(tmp_path) == ()
