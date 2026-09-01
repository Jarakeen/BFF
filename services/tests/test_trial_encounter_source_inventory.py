from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from services.trial_encounter_source_inventory import build_trial_encounter_source_inventory


def test_inventory_finds_local_layers_without_writing(tmp_path: Path):
    raw_dir = tmp_path / "bosses"
    packet_dir = tmp_path / "packets"
    raw_dir.mkdir()
    packet_dir.mkdir()

    (raw_dir / "odd_filename.json").write_text(
        json.dumps({"id": "oaxiltso", "name": "Oaxiltso"}),
        encoding="utf-8",
    )
    (packet_dir / "rockgrove_boss1.json").write_text(
        json.dumps(
            {
                "content_id": "rockgrove",
                "encounter_id": "oaxiltso",
                "encounter_name": "Oaxiltso",
                "evidence": [],
            }
        ),
        encoding="utf-8",
    )

    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE bosses (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE encounter (id TEXT PRIMARY KEY, content_id TEXT NOT NULL, name TEXT NOT NULL);
        INSERT INTO bosses(id, name) VALUES ('legacy_oax', 'Oaxiltso');
        INSERT INTO encounter(id, content_id, name) VALUES ('oaxiltso', 'rockgrove', 'Oaxiltso');
        """
    )

    rows = build_trial_encounter_source_inventory(
        connection,
        content_id="rockgrove",
        expected_names=("Oaxiltso", "Xalvakka"),
        raw_boss_dir=raw_dir,
        packet_dir=packet_dir,
        curated_strategy_names=("Oaxiltso",),
    )

    assert rows[0].raw_boss_files == ("odd_filename.json",)
    assert rows[0].legacy_boss_ids == ("legacy_oax",)
    assert rows[0].canonical_encounter_ids == ("oaxiltso",)
    assert rows[0].evidence_packets == ("rockgrove_boss1.json",)
    assert rows[0].has_curated_strategy is True

    assert rows[1].raw_boss_files == ()
    assert rows[1].legacy_boss_ids == ()
    assert rows[1].canonical_encounter_ids == ()
    assert rows[1].evidence_packets == ()
    assert rows[1].has_curated_strategy is False
