import json
from pathlib import Path

import pytest

from services.encounter_evidence_packet import load_encounter_evidence_packet


ROOT = Path(__file__).resolve().parents[2]


def _write_packet(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_encounter_evidence_packet_preserves_source_metadata(tmp_path: Path) -> None:
    path = _write_packet(
        tmp_path / "packet.json",
        {
            "schema_version": 1,
            "content_id": "rockgrove",
            "encounter_id": "oaxiltso",
            "encounter_name": "Oaxiltso",
            "evidence": [
                {
                    "fact_type": "transition",
                    "fact_key": "add_thresholds",
                    "value": {"thresholds": ["90%", "50%"]},
                    "source_type": "guide",
                    "source_name": "Example Guide",
                    "source_locator": "Boss section",
                    "source_revision": "rev-1",
                    "source_family": "example",
                    "game_update": "U51",
                    "patch_version": "11.1.0",
                    "confidence": "high",
                    "notes": "review note",
                }
            ],
        },
    )

    packet = load_encounter_evidence_packet(path)

    assert packet.schema_version == 1
    assert packet.content_id == "rockgrove"
    assert packet.encounter_id == "oaxiltso"
    assert packet.encounter_name == "Oaxiltso"
    assert len(packet.evidence) == 1
    row = packet.evidence[0]
    assert row.fact_type == "transition"
    assert row.source_family == "example"
    assert row.game_update == "U51"
    assert row.patch_version == "11.1.0"


def test_load_encounter_evidence_packet_allows_row_encounter_override(tmp_path: Path) -> None:
    path = _write_packet(
        tmp_path / "packet.json",
        {
            "encounter_id": "parent",
            "evidence": [
                {
                    "encounter_id": "child",
                    "fact_type": "mechanic_state",
                    "fact_key": "thing_exists",
                    "value": True,
                    "source_type": "uesp",
                    "source_name": "UESP",
                }
            ],
        },
    )

    packet = load_encounter_evidence_packet(path)

    assert packet.evidence[0].encounter_id == "child"


def test_load_encounter_evidence_packet_rejects_missing_encounter_id(tmp_path: Path) -> None:
    path = _write_packet(tmp_path / "packet.json", {"evidence": []})

    with pytest.raises(ValueError, match="missing encounter_id"):
        load_encounter_evidence_packet(path)


def test_load_encounter_evidence_packet_rejects_non_list_evidence(tmp_path: Path) -> None:
    path = _write_packet(
        tmp_path / "packet.json",
        {"encounter_id": "boss", "evidence": {}},
    )

    with pytest.raises(ValueError, match="evidence must be a list"):
        load_encounter_evidence_packet(path)


def test_real_encounter_evidence_packets_are_schema_valid() -> None:
    """Every checked-in canonical encounter evidence packet must satisfy the shared schema."""

    paths = sorted((ROOT / "data" / "encounter_evidence").glob("*.json"))
    assert paths, "expected checked-in encounter evidence packets"

    for path in paths:
        load_encounter_evidence_packet(path)


def test_canonical_encounter_evidence_ids_are_unique() -> None:
    """EncounterRepository indexes one canonical packet per encounter id."""

    paths = sorted((ROOT / "data" / "encounter_evidence").glob("*.json"))
    seen: dict[str, Path] = {}
    for path in paths:
        packet = load_encounter_evidence_packet(path)
        previous = seen.get(packet.encounter_id)
        assert previous is None, (
            f"duplicate canonical encounter_id {packet.encounter_id!r}: "
            f"{previous} and {path}"
        )
        seen[packet.encounter_id] = path


def test_supplemental_reference_evidence_packets_are_schema_valid() -> None:
    """Reference-only evidence may share encounter ids but must still parse cleanly."""

    paths = sorted((ROOT / "data" / "reference_evidence").glob("*.json"))
    assert paths, "expected supplemental Reference evidence packets"
    for path in paths:
        load_encounter_evidence_packet(path)
