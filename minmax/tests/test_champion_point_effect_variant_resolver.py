import sqlite3
from pathlib import Path

from minmax.champion_point_effect_variant_resolver import (
    ChampionPointEffectVariantResolver,
)
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.character_build.support_effect_resolver import effect_variant_to_support_effect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from models.build_model import ChampionPointEntry, PlayerBuild


FROM_THE_BRINK_DESCRIPTION = (
    "Whenever you heal yourself or an ally under |cffffff25|r% Health, you grant "
    "them a damage shield that absorbs up to |cffffff2200|r damage per stage, for "
    "|cffffff6|r seconds. This effect can occur once every |cffffff30|r seconds "
    "per target. Current bonus: |cffffff0|r damage absorption"
)


def _make_db(path: Path, *, description: str = FROM_THE_BRINK_DESCRIPTION) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE champion_point (
                name TEXT PRIMARY KEY,
                skill_type INTEGER,
                max_points INTEGER,
                jump_points TEXT,
                min_description TEXT,
                max_description TEXT,
                description TEXT
            );
            """
        )
        db.execute(
            """
            INSERT INTO champion_point
                (name, skill_type, max_points, jump_points,
                 min_description, max_description, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "From the Brink",
                1,
                50,
                "0,10,20,30,40,50",
                description,
                description,
                description,
            ),
        )


def test_from_the_brink_resolves_verified_five_stage_shield(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)

    effects, unresolved = ChampionPointEffectVariantResolver(db_path).resolve(
        "From the Brink",
        50,
    )

    assert unresolved == ()
    assert len(effects) == 1
    effect = effects[0]
    assert effect.name == "damage_shield"
    assert effect.layer == EffectLayer.PROC
    assert effect.source == "Champion Point: From the Brink"
    assert effect.magnitude == 11000.0
    assert effect.duration == 6.0
    assert effect.cooldown == 30.0
    assert effect.target_count == 1
    assert effect.target_type == SupportTargetType.ALLY
    assert effect.category == SupportEffectCategory.BUFF
    assert effect.trigger == "on_heal_target_below_25_percent_health"

    support = effect_variant_to_support_effect(effect)
    assert support.magnitude == 11000.0
    assert support.duration == 6.0
    assert support.cooldown == 30.0
    assert support.target_type == SupportTargetType.ALLY
    assert support.trigger is not None
    assert support.trigger.condition == (
        "heal_self_or_ally_below_25_percent_health; 30_second_cooldown_per_target"
    )


def test_from_the_brink_effect_math_clamps_to_current_db_cap(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)

    effects, unresolved = ChampionPointEffectVariantResolver(db_path).resolve(
        "From the Brink",
        60,
    )

    assert unresolved == ()
    assert effects[0].magnitude == 11000.0


def test_from_the_brink_fails_closed_when_source_record_changes(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(
        db_path,
        description=FROM_THE_BRINK_DESCRIPTION.replace("2200", "2300"),
    )

    effects, unresolved = ChampionPointEffectVariantResolver(db_path).resolve(
        "From the Brink",
        50,
    )

    assert effects == ()
    assert unresolved == (
        "Dynamic Champion Point source no longer matches verified mapping: From the Brink",
    )


def test_saved_build_adapter_attaches_verified_from_the_brink_effect(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)
    saved = PlayerBuild(
        Name="Magrat",
        BuildName="CP Dynamic",
        EsoClass="Warden",
        Role="Healer",
        ChampionPoints=[
            ChampionPointEntry(Name="From the Brink", Points="50"),
        ],
    )

    result = SavedBuildCharacterAdapter(db_path).adapt(saved)

    assert result.build is not None
    assert result.unresolved == ()
    assert len(result.build.champion_points) == 1
    allocation = result.build.champion_points[0]
    assert allocation.node_id == "from_the_brink"
    assert allocation.points == 50
    assert len(allocation.effects) == 1
    assert allocation.effects[0].name == "damage_shield"
    assert allocation.effects[0].magnitude == 11000.0
