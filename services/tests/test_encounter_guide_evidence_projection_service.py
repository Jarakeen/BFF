import json
from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_projection_builds_timeline_and_strategy_from_reviewed_evidence(tmp_path: Path):
    _write(
        tmp_path / "encounter_evidence" / "boss.json",
        {
            "schema_version": 1,
            "content_id": "trial",
            "encounter_id": "boss",
            "encounter_name": "Boss",
            "evidence": [
                {
                    "fact_type": "phase",
                    "fact_key": "phase_1",
                    "value": {"label": "Opening", "order": 1},
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
                {
                    "fact_type": "transition",
                    "fact_key": "execute_transition",
                    "value": {"threshold": "30%", "result": "execute"},
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
                {
                    "fact_type": "mechanic_state",
                    "fact_key": "big_blast_exists",
                    "value": True,
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
                {
                    "fact_type": "mechanic_detail",
                    "fact_key": "big_blast_behavior",
                    "value": {"target_count": 3, "radius_m": 8},
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
            ],
        },
    )
    _write(
        tmp_path / "reference_mitigations.json",
        {
            "schema_version": 1,
            "entries": [
                {
                    "entry_name": "Big Blast — Boss",
                    "mitigation": "Spread out.",
                    "source": "reviewed_encounter_evidence",
                }
            ],
        },
    )
    _write(
        tmp_path / "reference_common_names.json",
        {
            "schema_version": 1,
            "entries": [
                {
                    "entry_name": "Big Blast — Boss",
                    "common_names": ["Boom"],
                    "source": "player_raid_terminology",
                }
            ],
        },
    )

    projection = EncounterGuideEvidenceProjectionService(tmp_path).get("boss", "Boss")

    assert [(row.marker, row.label) for row in projection.timeline] == [
        ("P1", "Opening"),
        ("30%", "Execute Transition"),
    ]
    blast = next(row for row in projection.strategy if row.mechanic == "Big Blast")
    assert blast.common_names == ("Boom",)
    assert blast.mitigation == "Spread out."
    assert "Target Count: 3" in blast.summary
    assert projection.callouts == ("Big Blast: Spread out.",)


def test_real_dsr_twins_projection_exposes_timeline_and_strategy():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "lylanar_turlassil", "Lylanar and Turlassil"
    )

    assert any(row.label == "Hounds" for row in projection.timeline)
    assert any(row.label == "Brothers Reunited" for row in projection.timeline)
    names = {row.mechanic for row in projection.strategy}
    assert "Destructive Ember" in names
    assert "Synchronized Kill" in names
    synced = next(row for row in projection.strategy if row.mechanic == "Synchronized Kill")
    assert "7.5 seconds" in synced.mitigation


def test_real_reef_guardian_projection_exposes_replication_strategy():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "reef_guardian", "Reef Guardian"
    )

    replication = next(row for row in projection.strategy if row.mechanic == "Replication")
    assert "80%" in replication.mitigation
    assert "50%" in replication.mitigation
    assert "HM" in replication.mitigation
