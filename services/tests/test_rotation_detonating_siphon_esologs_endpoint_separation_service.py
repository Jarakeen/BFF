import json
import sqlite3

import pytest

from services.rotation_detonating_siphon_esologs_endpoint_separation_service import (
    RotationDetonatingSiphonEndpointSeparationService,
)


def _db(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
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
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "R",
                1,
                timestamp,
                event_type,
                source_id,
                target_id,
                ability_id,
                track_id,
                json.dumps(payload),
            ),
        )


def test_separation_thresholds_isolate_discriminating_endpoint_hits(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path)

    # Cast endpoints are 12 normalized units apart.
    _row(
        path,
        timestamp=1000,
        event_type="cast",
        source_id=1,
        target_id=90,
        ability_id=500,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(1200, 0),
    )
    # Caster-only hit at x=2.
    _row(
        path,
        timestamp=1100,
        event_type="damage",
        source_id=1,
        target_id=10,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(200, 0),
    )
    # Cast-target-only hit at x=10.
    _row(
        path,
        timestamp=1200,
        event_type="damage",
        source_id=1,
        target_id=11,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(1000, 0),
    )
    # Beyond both endpoint circles but on the segment at x=6.
    _row(
        path,
        timestamp=1300,
        event_type="damage",
        source_id=1,
        target_id=12,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(600, 0),
    )

    report = RotationDetonatingSiphonEndpointSeparationService(path).inspect(
        cast_ability_ids=(500,),
        minimum_separations=(5.0, 10.0, 15.0),
    )

    assert report.cast_count_with_positions == 1
    assert report.median_endpoint_separation == pytest.approx(12.0)
    assert report.maximum_endpoint_separation == pytest.approx(12.0)
    assert report.separation_p90 == pytest.approx(12.0)

    by_threshold = {item.minimum_separation: item for item in report.thresholds}
    ten = by_threshold[10.0]
    assert ten.cast_count == 1
    assert ten.events_with_positions == 3
    assert ten.caster_only_count == 1
    assert ten.cast_target_only_count == 1
    assert ten.within_both_count == 0
    assert ten.beyond_both_count == 1
    assert ten.median_target_to_segment_distance_for_beyond_both == pytest.approx(0.0)

    fifteen = by_threshold[15.0]
    assert fifteen.cast_count == 0
    assert fifteen.linked_event_count == 0
    assert any("does not contain cast endpoints" in item for item in report.unresolved)


def test_overlapping_endpoint_circles_are_not_mistaken_for_discriminating_hits(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path)
    _row(
        path,
        timestamp=1000,
        event_type="cast",
        source_id=1,
        target_id=90,
        ability_id=500,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(300, 0),
    )
    _row(
        path,
        timestamp=1100,
        event_type="damage",
        source_id=1,
        target_id=10,
        ability_id=118766,
        track_id=77,
        source_xy=(0, 0),
        target_xy=(150, 0),
    )

    report = RotationDetonatingSiphonEndpointSeparationService(path).inspect(
        cast_ability_ids=(500,),
        minimum_separations=(0.0, 5.0),
    )

    by_threshold = {item.minimum_separation: item for item in report.thresholds}
    zero = by_threshold[0.0]
    assert zero.within_both_count == 1
    assert zero.caster_only_count == 0
    assert zero.cast_target_only_count == 0

    five = by_threshold[5.0]
    assert five.cast_count == 0
    assert five.events_with_positions == 0
