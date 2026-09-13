import json
import sqlite3

import pytest

from services.rotation_detonating_siphon_esologs_spatial_topology_service import (
    RotationDetonatingSiphonEsoLogsSpatialTopologyService,
)


def _db(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                target_id INTEGER,
                ability_game_id INTEGER,
                cast_track_id INTEGER,
                raw_json TEXT
            )
            """
        )


def _row(
    path,
    *,
    index,
    timestamp,
    event_type,
    source_id,
    target_id,
    ability_id,
    track_id,
    source_xy=None,
    target_xy=None,
):
    payload = {}
    if source_xy is not None:
        payload["sourceResources"] = {"x": source_xy[0], "y": source_xy[1]}
    if target_xy is not None:
        payload["targetResources"] = {"x": target_xy[0], "y": target_xy[1]}
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "R",
                1,
                index,
                timestamp,
                event_type,
                source_id,
                target_id,
                ability_id,
                track_id,
                json.dumps(payload),
            ),
        )


def test_topology_normalizes_documented_100x_coordinates_and_measures_endpoints(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path)
    _row(
        path,
        index=1,
        timestamp=1000,
        event_type="cast",
        source_id=1,
        target_id=90,
        ability_id=500,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(1200, 0),
    )
    # 2 units from caster, 10 from cast-target candidate.
    _row(
        path,
        index=2,
        timestamp=1100,
        event_type="damage",
        source_id=1,
        target_id=10,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(200, 0),
    )
    # 2 units from cast-target candidate, 10 from caster.
    _row(
        path,
        index=3,
        timestamp=1200,
        event_type="damage",
        source_id=1,
        target_id=11,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(1000, 0),
    )
    # 6 units from both endpoint centers but directly on the segment.
    _row(
        path,
        index=4,
        timestamp=1300,
        event_type="damage",
        source_id=1,
        target_id=12,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(600, 0),
    )

    report = RotationDetonatingSiphonEsoLogsSpatialTopologyService(path).inspect(
        cast_ability_ids=(500,),
    )

    assert report.cast_count == 1
    assert report.linked_event_count == 3
    assert report.events_with_actor_positions == 3
    assert report.events_with_cast_target_position == 3
    assert report.within_radius_of_caster_count == 1
    assert report.within_radius_of_cast_target_count == 1
    assert report.within_radius_of_either_endpoint_count == 2
    assert report.beyond_both_endpoint_radius_count == 1
    assert report.median_target_to_caster_distance == pytest.approx(6.0)
    assert report.median_target_to_cast_target_distance == pytest.approx(6.0)
    assert report.median_target_to_segment_distance == pytest.approx(0.0)
    assert report.maximum_target_to_segment_distance == pytest.approx(0.0)
    assert report.unresolved == ()


def test_missing_cast_target_position_remains_explicitly_unresolved(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path)
    _row(
        path,
        index=1,
        timestamp=1000,
        event_type="cast",
        source_id=1,
        target_id=90,
        ability_id=500,
        track_id=77,
        source_xy=(0, 0),
    )
    _row(
        path,
        index=2,
        timestamp=1100,
        event_type="damage",
        source_id=1,
        target_id=10,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(200, 0),
    )

    report = RotationDetonatingSiphonEsoLogsSpatialTopologyService(path).inspect(
        cast_ability_ids=(500,),
    )

    assert report.events_with_actor_positions == 1
    assert report.events_with_cast_target_position == 0
    assert report.within_radius_of_caster_count == 1
    assert report.within_radius_of_cast_target_count == 0
    assert report.median_target_to_cast_target_distance is None
    assert any("cast rows expose no usable" in item for item in report.unresolved)


def test_same_cast_target_actor_damage_rows_report_anchor_drift(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path)
    _row(
        path,
        index=1,
        timestamp=1000,
        event_type="cast",
        source_id=1,
        target_id=90,
        ability_id=500,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(1000, 1000),
    )
    _row(
        path,
        index=2,
        timestamp=1100,
        event_type="damage",
        source_id=1,
        target_id=90,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(1030, 1040),
    )

    report = RotationDetonatingSiphonEsoLogsSpatialTopologyService(path).inspect(
        cast_ability_ids=(500,),
    )

    assert report.cast_target_actor_count == 1
    assert report.cast_target_position_stability_samples == 1
    assert report.median_cast_target_position_drift == pytest.approx(0.5)
