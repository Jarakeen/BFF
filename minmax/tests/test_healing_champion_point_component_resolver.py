import sqlite3

from minmax.character_build.champion_points import ChampionPointAllocation
from minmax.healing_champion_point_component_resolver import (
    HealingChampionPointComponentResolver,
)


def _database(path, *, swift_link=False, is_dot=1, is_aoe=1, effect_kind="heal"):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE skill_rank (
            id INTEGER PRIMARY KEY,
            skill_id INTEGER,
            ability_id INTEGER
        );
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
        CREATE TABLE champion_point_skill_rank (
            id INTEGER PRIMARY KEY,
            champion_point_id INTEGER NOT NULL,
            skill_rank_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            ability_id INTEGER,
            relationship TEXT NOT NULL,
            condition TEXT,
            source TEXT,
            confidence TEXT,
            source_url TEXT,
            raw_source TEXT
        );
        CREATE TABLE skill_component_classification (
            skill_rank_id INTEGER NOT NULL,
            coefficient_number INTEGER NOT NULL,
            effect_kind TEXT,
            damage_type TEXT,
            is_dot INTEGER,
            is_aoe INTEGER,
            can_crit INTEGER,
            source TEXT,
            confidence REAL
        );

        INSERT INTO skill VALUES (10, 'Necrotic Orb');
        INSERT INTO skill_rank VALUES (100, 10, 42028);
        INSERT INTO champion_point VALUES
            (1, 'Rejuvenator', 1, 50, '0,10,20,30,40,50',
             'Grants 41 Weapon and Spell Damage to your healing abilities per stage.', NULL, NULL),
            (2, 'Soothing Tide', 1, 50, '0,10,20,30,40,50',
             'Increases your Healing Done by area of effect heals by 2% per stage.', NULL, NULL),
            (3, 'Swift Renewal', 1, 50, '0,10,20,30,40,50',
             'Increases your Healing Done with healing over time effects by 2% per stage.', NULL, NULL);

        INSERT INTO champion_point_skill_rank VALUES
            (1, 1, 100, 10, 42028, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit', 'energy-orb', 'Energy Orb -> Rejuvenator'),
            (2, 2, 100, 10, 42028, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit', 'energy-orb', 'Energy Orb -> Soothing Tide');
        """
    )
    if swift_link:
        db.execute(
            """INSERT INTO champion_point_skill_rank VALUES
               (3, 3, 100, 10, 42028, 'Buffs', 'only while slotted', 'ESO-Hub', 'Explicit',
                'example', 'Example -> Swift Renewal')"""
        )
    db.execute(
        """
        INSERT INTO skill_component_classification (
            skill_rank_id, coefficient_number, effect_kind, damage_type,
            is_dot, is_aoe, can_crit, source, confidence
        ) VALUES (100, 1, ?, NULL, ?, ?, 1, 'fixture', 1.0)
        """,
        (effect_kind, is_dot, is_aoe),
    )
    db.commit()
    db.close()


def _allocations(*, points=50):
    return (
        ChampionPointAllocation(node_id="rejuvenator", points=points),
        ChampionPointAllocation(node_id="soothing_tide", points=points),
        ChampionPointAllocation(node_id="swift_renewal", points=points),
    )


def test_explicit_rank_links_gate_energy_orb_style_component(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, swift_link=False, is_dot=1, is_aoe=1)

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 205.0
    assert result.healing_done_percent == 10.0
    assert result.applied == ("Rejuvenator", "Soothing Tide")
    assert "Swift Renewal" not in result.applied
    assert result.unresolved == ()


def test_hot_and_aoe_bonuses_share_one_additive_bucket(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, swift_link=True, is_dot=1, is_aoe=1)

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 205.0
    assert result.healing_done_percent == 20.0
    assert result.applied == ("Rejuvenator", "Swift Renewal", "Soothing Tide")


def test_component_semantics_narrow_explicit_relationships(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, swift_link=True, is_dot=0, is_aoe=0)

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 205.0
    assert result.healing_done_percent == 0.0
    assert result.applied == ("Rejuvenator",)


def test_unknown_component_semantics_remain_unresolved(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, swift_link=True, is_dot=None, is_aoe=None)

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 205.0
    assert result.healing_done_percent == 0.0
    assert any("Swift Renewal" in item and "periodicity unknown" in item for item in result.unresolved)
    assert any("Soothing Tide" in item and "target shape unknown" in item for item in result.unresolved)


def test_only_while_slotted_is_not_assumed_true(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, swift_link=True)

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=False,
    )

    assert result.power_bonus == 0.0
    assert result.healing_done_percent == 0.0
    assert result.applied == ()


def test_non_healing_component_is_unaffected(tmp_path):
    path = tmp_path / "eso.db"
    _database(path, swift_link=True, effect_kind="damage")

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 0.0
    assert result.healing_done_percent == 0.0
    assert result.unresolved == ()


def test_source_drift_fails_closed(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE champion_point SET min_description='Changed by a future ESO update.' WHERE name='Rejuvenator'"
        )
        db.commit()

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=_allocations(),
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 0.0
    assert result.healing_done_percent == 10.0
    assert "Rejuvenator" not in result.applied
    assert any("source no longer matches" in item and "Rejuvenator" in item for item in result.unresolved)


def test_saved_points_are_clamped_without_mutating_allocation(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    allocations = _allocations(points=999)

    result = HealingChampionPointComponentResolver(path).resolve(
        allocations=allocations,
        skill_rank_id=100,
        coefficient_number=1,
        is_slotted=True,
    )

    assert result.power_bonus == 205.0
    assert result.healing_done_percent == 10.0
    assert allocations[0].points == 999
