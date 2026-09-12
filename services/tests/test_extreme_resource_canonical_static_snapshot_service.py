from __future__ import annotations

import sqlite3

from minmax.gear_set_repository import GearSetRepository
from services.extreme_resource_canonical_static_snapshot_service import (
    ExtremeResourceCanonicalStaticSnapshotService,
)
from services.extreme_resource_champion_point_state_service import (
    ExtremeResourceChampionPointStateService,
)
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)
from services.service_catalog import SERVICE_CATALOG


def _write_minimal_static_db(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                class_type TEXT,
                skill_line TEXT,
                skill_type TEXT,
                is_passive INTEGER NOT NULL,
                is_player INTEGER NOT NULL,
                is_crafted INTEGER NOT NULL DEFAULT 0,
                base_ability_id INTEGER,
                description TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                ability_id INTEGER NOT NULL
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                description TEXT
            );
            INSERT INTO skill VALUES (
                1, 'Syrabane''s Boon', '', 'High Elf Skills', 'Passive',
                1, 1, 0, NULL, 'fixture'
            );
            INSERT INTO skill_rank VALUES (1, 1, 3, 1001);
            INSERT INTO ability VALUES (1001, 'Increases your Max Magicka by 2000');

            CREATE TABLE champion_point (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                min_description TEXT,
                max_description TEXT,
                description TEXT
            );
            INSERT INTO champion_point VALUES (
                1, 'Eldritch Insight', 0, 20, '', NULL, NULL,
                'Grants 26 Max Magicka per stage.'
            );
            INSERT INTO champion_point VALUES (
                2, 'Arcane Supremacy', 2, 50, '', NULL, NULL,
                'Grants 28 Max Magicka per stage.'
            );

            CREATE TABLE armor_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT
            );
            INSERT INTO armor_glyph VALUES (1, 'Glyph of Magicka');

            CREATE TABLE jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT
            );
            INSERT INTO jewelry_glyph VALUES (1, 'Glyph of Increase Magical Harm');
            """
        )


def test_static_snapshot_is_reused_per_resolved_database_path(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_minimal_static_db(path)

    first = ExtremeResourceCanonicalStaticSnapshotService(path).build()
    second = ExtremeResourceCanonicalStaticSnapshotService(path.parent / "." / path.name).build()

    assert second is first
    assert second.champion_point_repository is first.champion_point_repository
    assert second.skill_universe_service is first.skill_universe_service
    assert second.racial_passive_repository is first.racial_passive_repository


def test_static_snapshot_preloads_only_canonical_evidence_not_objective_math(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_minimal_static_db(path)

    snapshot = ExtremeResourceCanonicalStaticSnapshotService(path).build()

    assert snapshot.preload_complete is True
    assert [row.name for row in snapshot.player_skills] == ["Syrabane's Boon"]
    assert [row.name for row in snapshot.champion_points_non_slottable] == [
        "Eldritch Insight"
    ]
    assert [row.name for row in snapshot.champion_points_slottable] == [
        "Arcane Supremacy"
    ]
    assert snapshot.armor_glyph_names == ("Glyph of Magicka",)
    assert snapshot.jewelry_glyph_names == ("Glyph of Increase Magical Harm",)


def test_static_snapshot_is_the_single_repository_owner_for_extreme_consumers(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_minimal_static_db(path)
    snapshot = ExtremeResourceCanonicalStaticSnapshotService(path).build()

    factory = ExtremeResourceConditionedPhase5ContextFactory(
        gear_set_repository=GearSetRepository(path),
    )
    champion_points = ExtremeResourceChampionPointStateService(path)

    assert factory.gear_resolver is not None
    assert factory.gear_resolver.armor_glyph_repository is snapshot.armor_glyph_repository
    assert factory.gear_resolver.jewelry_glyph_repository is snapshot.jewelry_glyph_repository
    assert factory.gear_resolver.jewelry_trait_repository is snapshot.jewelry_trait_repository
    assert factory.skill_line_repository is snapshot.skill_line_repository
    assert factory.racial_passive_repository is snapshot.racial_passive_repository
    assert champion_points.repository is snapshot.champion_point_repository


def test_static_snapshot_preload_failure_stays_explicit_and_does_not_invent_evidence(tmp_path) -> None:
    path = tmp_path / "empty.db"
    path.touch()

    snapshot = ExtremeResourceCanonicalStaticSnapshotService(path).build()

    assert snapshot.preload_complete is False
    assert snapshot.player_skills == ()
    assert snapshot.champion_points_non_slottable == ()
    assert snapshot.champion_points_slottable == ()
    assert snapshot.armor_glyph_names == ()
    assert snapshot.jewelry_glyph_names == ()
    assert snapshot.preload_unresolved


def test_static_snapshot_responsibility_is_registered_in_canonical_service_catalog() -> None:
    descriptor = SERVICE_CATALOG.get("extreme.resource_canonical_static_snapshot")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.extreme_resource_canonical_static_snapshot_service"
    )
    assert descriptor.responsibilities == (
        "extreme_resource_canonical_static_evidence_snapshot",
    )
