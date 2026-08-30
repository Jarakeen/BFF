from __future__ import annotations

import json
import sqlite3

from models.build_model import ChampionPointEntry, PlayerBuild
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId


def _static_db(tmp_path):
    path = tmp_path / "eso.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE champion_point (
            name TEXT PRIMARY KEY,
            skill_type INTEGER,
            max_points INTEGER,
            jump_points TEXT,
            description TEXT,
            min_description TEXT,
            max_description TEXT
        );
        CREATE TABLE entity (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL
        );
        CREATE TABLE entity_source (
            id INTEGER PRIMARY KEY,
            entity_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_entity_type TEXT,
            source_id TEXT,
            source_name TEXT,
            raw_json TEXT
        );
        """
    )
    db.execute(
        "INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Boundless Vitality",
            1,
            50,
            "",
            "",
            "Grants 28 Max Health per stage.",
            "Grants 28 Max Health per stage.",
        ),
    )
    db.execute("INSERT INTO entity VALUES ('food:test', 'food', 'Health Food', 'health-food')")
    db.execute(
        "INSERT INTO entity_source(entity_id, source, source_entity_type, source_id, source_name, raw_json) VALUES (?, 'ESO', 'food', '1', ?, ?)",
        (
            "food:test",
            "Health Food",
            json.dumps({"abilityDesc": "Increase Max Health by 4462 for 2 hours."}),
        ),
    )
    db.commit()
    db.close()
    return path


def test_factory_applies_cp_and_food_to_final_character_state(tmp_path):
    path = _static_db(tmp_path)
    build = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Boundless Vitality", Points="20")],
        Food="Health Food",
    )
    progression = CharacterProgression(
        attributes=AttributeAllocation(health=64),
    )
    factory = BuildCalculationContextFactory(
        champion_point_repository=ChampionPointStaticRepository(path),
        provisioning_repository=ProvisioningStaticRepository(path),
    )

    context = factory.build(
        character_id="character-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    # 16,000 base + 64*122 attributes + 20*28 CP + 4,462 food.
    assert context.character_state.max_health == 28830
    trace = context.character_state.traces[StatId.MAX_HEALTH]
    assert any(step.label == "Champion Point flat" and step.value == 560 for step in trace.steps)
    assert any(step.label == "food flat" and step.value == 4462 for step in trace.steps)
    assert context.unresolved_gear_effects == ()
