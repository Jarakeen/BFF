from __future__ import annotations

import sqlite3

from services.extreme_skill_universe_service import (
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


def _db(tmp_path):
    path = tmp_path / "skills.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE skill(
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
        CREATE TABLE skill_rank(
            id INTEGER PRIMARY KEY,
            skill_id INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            ability_id INTEGER NOT NULL
        );
        CREATE TABLE ability(
            ability_id INTEGER PRIMARY KEY,
            description TEXT
        );
        """
    )

    rows = [
        (1, "Frozen Armor", "Warden", "Winter's Embrace", "Passive", 1, 1, 0, 1001, "Class passive."),
        (2, "Heavy Weapons", "", "Two Handed", "Passive", 1, 1, 0, 1002, "Weapon passive."),
        (3, "Dexterity", "", "Medium Armor", "Passive", 1, 1, 0, 1003, "Armor passive."),
        (4, "Slayer", "", "Fighters Guild", "Passive", 1, 1, 0, 1004, "Guild passive."),
        (5, "Magicka Aid", "", "Support", "Passive", 1, 1, 0, 1005, "Alliance passive."),
        (6, "Undeath", "", "Vampire", "Passive", 1, 1, 0, 1006, "World passive."),
        (7, "Feline Ambush", "", "Khajiit Skills", "Passive", 1, 1, 0, 1007, "Racial passive."),
        (8, "Medicinal Use", "", "Alchemy", "Passive", 1, 1, 0, 1008, "Craft passive."),
        (9, "Keen Eye", "", "Scrying", "Passive", 1, 1, 0, 1009, "Utility passive."),
        (10, "Wall of Elements", "", "Destruction Staff", "Active", 0, 1, 0, 1010, "Active skill."),
        (11, "Combat Prayer", "", "Restoration Staff", "Active", 0, 1, 0, 1011, "Active skill."),
    ]
    db.executemany(
        """
        INSERT INTO skill(
            id,name,class_type,skill_line,skill_type,is_passive,is_player,
            is_crafted,base_ability_id,description
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    for skill_id in range(1, 12):
        ability_id = 2000 + skill_id
        db.execute(
            "INSERT INTO skill_rank(id,skill_id,rank,ability_id) VALUES (?,?,?,?)",
            (skill_id, skill_id, 2, ability_id),
        )
        db.execute(
            "INSERT INTO ability(ability_id,description) VALUES (?,?)",
            (ability_id, f"Concrete description {skill_id}."),
        )
    db.commit()
    db.close()
    return path


def test_every_player_skill_is_retained_and_classified(tmp_path):
    rows = ExtremeSkillUniverseService(_db(tmp_path)).all_player_skills()

    assert len(rows) == 11
    by_name = {row.name: row for row in rows}
    assert by_name["Frozen Armor"].domain is ExtremeSkillDomain.CLASS
    assert by_name["Heavy Weapons"].domain is ExtremeSkillDomain.WEAPON
    assert by_name["Dexterity"].domain is ExtremeSkillDomain.ARMOR
    assert by_name["Slayer"].domain is ExtremeSkillDomain.GUILD
    assert by_name["Magicka Aid"].domain is ExtremeSkillDomain.ALLIANCE_WAR
    assert by_name["Undeath"].domain is ExtremeSkillDomain.WORLD
    assert by_name["Feline Ambush"].domain is ExtremeSkillDomain.RACIAL
    assert by_name["Medicinal Use"].domain is ExtremeSkillDomain.CRAFT
    assert by_name["Keen Eye"].domain is ExtremeSkillDomain.UTILITY


def test_passive_and_active_views_partition_the_player_universe(tmp_path):
    service = ExtremeSkillUniverseService(_db(tmp_path))
    all_rows = service.all_player_skills()
    passives = service.passives()
    actives = service.actives()

    assert len(passives) == 9
    assert len(actives) == 2
    assert {row.skill_id for row in all_rows} == {
        *(row.skill_id for row in passives),
        *(row.skill_id for row in actives),
    }


def test_max_rank_identity_and_concrete_description_are_preserved(tmp_path):
    row = next(
        row
        for row in ExtremeSkillUniverseService(_db(tmp_path)).all_player_skills()
        if row.name == "Frozen Armor"
    )

    assert row.max_rank == 2
    assert row.max_rank_ability_id == 2001
    assert row.description == "Concrete description 1."


def test_known_noncombat_lines_remain_in_universe_but_are_marked_noncombat(tmp_path):
    rows = ExtremeSkillUniverseService(_db(tmp_path)).all_player_skills()
    by_name = {row.name: row for row in rows}

    assert by_name["Medicinal Use"].known_noncombat_line is True
    assert by_name["Keen Eye"].known_noncombat_line is True
    assert by_name["Wall of Elements"].known_noncombat_line is False


def test_player_skill_universe_is_shared_across_service_instances(tmp_path, monkeypatch):
    path = _db(tmp_path)
    cache_key = str(path.resolve())
    ExtremeSkillUniverseService._production_universe_cache.pop(cache_key, None)

    import services.extreme_skill_universe_service as module

    real_connect = module.sqlite3.connect
    connect_calls = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_calls
        connect_calls += 1
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(module.sqlite3, "connect", counting_connect)

    first = ExtremeSkillUniverseService(path)
    second = ExtremeSkillUniverseService(path)

    first_rows = first.passives()
    second_rows = second.actives()

    assert len(first_rows) == 9
    assert len(second_rows) == 2
    assert connect_calls == 1
