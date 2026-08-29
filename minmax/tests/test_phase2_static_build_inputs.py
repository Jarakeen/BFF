from __future__ import annotations

import json
import sqlite3

from models.build_model import ChampionPointEntry, PlayerBuild
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.static_build_inputs import StaticBuildInputResolver
from minmax.stat_ids import StatId


def _db(tmp_path):
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    connection.executescript(
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
    connection.commit()
    return path, connection


def test_cp_static_repository_uses_completed_stage_thresholds(tmp_path):
    path, db = _db(tmp_path)
    db.execute(
        "INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Threshold Health Test",
            0,
            50,
            "0,10,20,30,40,50",
            "",
            "Grants |cffffff28|r Max Health per stage.",
            "Grants |cffffff28|r Max Health per stage.",
        ),
    )
    db.commit()
    db.close()

    effects, unresolved = ChampionPointStaticRepository(path).resolve("Threshold Health Test", 35)

    assert unresolved == []
    assert len(effects) == 1
    assert effects[0].stat is StatId.MAX_HEALTH
    assert effects[0].value == 84.0


def test_cp_static_repository_supports_per_point_stars(tmp_path):
    path, db = _db(tmp_path)
    db.execute(
        "INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Boundless Vitality",
            0,
            50,
            "",
            "",
            "Grants |cffffff28|r Max Health per stage.",
            "Grants |cffffff28|r Max Health per stage.",
        ),
    )
    db.commit()
    db.close()

    effects, unresolved = ChampionPointStaticRepository(path).resolve("Boundless Vitality", 20)

    assert unresolved == []
    assert effects[0].value == 560.0


def test_cp_dynamic_star_stays_explicitly_unresolved(tmp_path):
    path, db = _db(tmp_path)
    db.execute(
        "INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Backstabber",
            1,
            50,
            "0,10,20,30,40,50",
            "",
            "Increases your Critical Damage done by 2% per stage when you are flanking an enemy.",
            "Increases your Critical Damage done by 2% per stage when you are flanking an enemy.",
        ),
    )
    db.commit()
    db.close()

    effects, unresolved = ChampionPointStaticRepository(path).resolve("Backstabber", 50)

    assert effects == []
    assert unresolved == ["Champion Point is dynamic or not yet stat-mapped: Backstabber"]


def test_provisioning_repository_uses_cp160_endpoint_for_range_tooltips(tmp_path):
    path, db = _db(tmp_path)
    db.execute("INSERT INTO entity VALUES ('food:test', 'food', 'Consummate Test', 'consummate-test')")
    db.execute(
        "INSERT INTO entity_source(entity_id, source, source_entity_type, source_id, source_name, raw_json) VALUES (?, 'ESO', 'food', '1', ?, ?)",
        (
            "food:test",
            "Consummate Test",
            json.dumps(
                {
                    "level": "5-CP160",
                    "abilityDesc": "Increase Max Health, Magicka and Stamina by |cffffff490-4312|r for |cffffff2|r hours.",
                }
            ),
        ),
    )
    db.commit()
    db.close()

    effects, unresolved = ProvisioningStaticRepository(path).resolve("Consummate Test")

    assert unresolved == []
    assert {effect.stat: effect.value for effect in effects} == {
        StatId.MAX_HEALTH: 4312.0,
        StatId.MAX_MAGICKA: 4312.0,
        StatId.MAX_STAMINA: 4312.0,
    }


def test_provisioning_repository_resolves_mixed_recovery_values(tmp_path):
    path, db = _db(tmp_path)
    db.execute("INSERT INTO entity VALUES ('drink:test', 'drink', 'Recovery Test', 'recovery-test')")
    db.execute(
        "INSERT INTO entity_source(entity_id, source, source_entity_type, source_id, source_name, raw_json) VALUES (?, 'ESO', 'drink', '2', ?, ?)",
        (
            "drink:test",
            "Recovery Test",
            json.dumps(
                {
                    "abilityDesc": "Increase Health Recovery by |cffffff341|r and Magicka and Stamina Recovery by |cffffff313|r for |cffffff2|r hours."
                }
            ),
        ),
    )
    db.commit()
    db.close()

    effects, unresolved = ProvisioningStaticRepository(path).resolve("Recovery Test")

    assert unresolved == []
    assert {effect.stat: effect.value for effect in effects} == {
        StatId.HEALTH_RECOVERY: 341.0,
        StatId.MAGICKA_RECOVERY: 313.0,
        StatId.STAMINA_RECOVERY: 313.0,
    }


def test_static_resolver_applies_cp_and_food_to_distinct_resource_buckets(tmp_path):
    path, db = _db(tmp_path)
    db.execute(
        "INSERT INTO champion_point VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Boundless Vitality",
            0,
            50,
            "",
            "",
            "Grants 28 Max Health per stage.",
            "Grants 28 Max Health per stage.",
        ),
    )
    db.execute("INSERT INTO entity VALUES ('food:test', 'food', 'Health Food', 'health-food')")
    db.execute(
        "INSERT INTO entity_source(entity_id, source, source_entity_type, source_id, source_name, raw_json) VALUES (?, 'ESO', 'food', '3', ?, ?)",
        ("food:test", "Health Food", json.dumps({"abilityDesc": "Increase Max Health by 4462 for 2 hours."})),
    )
    db.commit()
    db.close()

    build = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Boundless Vitality", Points="20")],
        Food="Health Food",
    )
    resolver = StaticBuildInputResolver(
        champion_point_repository=ChampionPointStaticRepository(path),
        provisioning_repository=ProvisioningStaticRepository(path),
    )

    result = resolver.apply(GearCalculationInputs(), build)

    assert result.health.champion_flat == 560.0
    assert result.health.food_flat == 4462.0
    assert result.unresolved == ()
