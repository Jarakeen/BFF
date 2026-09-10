import json
from pathlib import Path

from ui.reference_encounter_evidence import load_reviewed_encounter_evidence_entries


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


def _packet(root: Path, encounter_id: str, encounter_name: str, evidence: list[dict]) -> None:
    _write(
        root / "encounter_evidence" / f"{encounter_id}.json",
        {
            "schema_version": 1,
            "content_id": "dreadsail_reef",
            "encounter_id": encounter_id,
            "encounter_name": encounter_name,
            "evidence": evidence,
        },
    )


def test_backed_boss_with_no_canonical_mechanic_surfaces_reviewed_evidence(tmp_path):
    _boss(tmp_path, "reef_guardian", "Reef Guardian")
    _packet(
        tmp_path,
        "reef_guardian",
        "Reef Guardian",
        [
            {
                "fact_type": "mechanic_state",
                "fact_key": "acid_reflux_exists",
                "value": True,
                "source_type": "guide",
                "source_name": "Guide A",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic_detail",
                "fact_key": "acid_reflux_core_behavior",
                "value": {
                    "target": "taunt_target",
                    "leaves_acid_pools": True,
                    "applies_stacking_acid_vulnerability": True,
                },
                "source_type": "guide",
                "source_name": "Guide A",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic_detail",
                "fact_key": "acid_reflux_timing",
                "value": {
                    "duration_seconds_approx": 10,
                    "acid_pool_interval_seconds_approx": 2,
                    "acid_pool_count": 5,
                },
                "source_type": "guide",
                "source_name": "Guide B",
                "confidence": "high",
            },
        ],
    )

    entries = load_reviewed_encounter_evidence_entries(tmp_path)
    acid = next(entry for entry in entries if entry.name == "Acid Reflux — Reef Guardian")

    text = acid.detail_text()
    assert "Acid Reflux Core Behavior" in text
    assert "Taunt Target" in text
    assert "Leaves Acid Pools: Yes" in text
    assert "Acid Pool Count: 5" in text
    assert "Duration Seconds Approx: 10" in text


def test_mechanic_state_exists_creates_human_readable_entry_name(tmp_path):
    _packet(
        tmp_path,
        "tideborn_taleria",
        "Tideborn Taleria",
        [
            {
                "fact_type": "mechanic_state",
                "fact_key": "rapid_deluge_exists",
                "value": True,
                "source_type": "uesp",
                "source_name": "UESP",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic_detail",
                "fact_key": "rapid_deluge_veteran_behavior",
                "value": {
                    "target_count": 5,
                    "detonation_seconds_approx": 6,
                    "swimming_mitigates_blast": True,
                },
                "source_type": "guide",
                "source_name": "Reviewed Guide",
                "confidence": "high",
            },
        ],
    )

    entries = load_reviewed_encounter_evidence_entries(tmp_path)
    rapid = next(entry for entry in entries if entry.name == "Rapid Deluge — Tideborn Taleria")

    assert "Target Count: 5" in rapid.detail_text()
    assert "Detonation Seconds Approx: 6" in rapid.detail_text()
    assert "Swimming Mitigates Blast: Yes" in rapid.detail_text()


def test_conflicting_related_fact_is_not_joined_into_mechanic_entry(tmp_path):
    _packet(
        tmp_path,
        "reef_guardian",
        "Reef Guardian",
        [
            {
                "fact_type": "mechanic_state",
                "fact_key": "heartburn_exists",
                "value": True,
                "source_type": "guide",
                "source_name": "Guide A",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic_detail",
                "fact_key": "heartburn_duration_seconds",
                "value": 60,
                "source_type": "guide",
                "source_name": "Guide A",
                "confidence": "high",
            },
            {
                "fact_type": "mechanic_detail",
                "fact_key": "heartburn_duration_seconds",
                "value": 45,
                "source_type": "guide",
                "source_name": "Guide B",
                "confidence": "high",
            },
        ],
    )

    entries = load_reviewed_encounter_evidence_entries(tmp_path)
    heartburn = next(entry for entry in entries if entry.name == "Heartburn — Reef Guardian")

    assert "Heartburn Duration Seconds" not in heartburn.detail_text()
