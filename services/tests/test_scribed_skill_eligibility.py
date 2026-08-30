from services.skill_bar_eligibility import filter_skill_choices, is_player_active


def _raw_crafted(name="Raw Crafted"):
    return {
        "id": 9001,
        "ability_id": 9001,
        "base_ability_id": 9001,
        "name": name,
        "is_player": 1,
        "is_passive": 0,
        "is_crafted": 1,
        "skill_line": "Soul Magic",
        "class_type": "",
        "base_mechanic": 0,
    }


def _configured(name, synthetic_id):
    skill = _raw_crafted(name)
    skill.update(
        {
            "id": synthetic_id,
            "ability_id": synthetic_id,
            "base_ability_id": synthetic_id,
            "scribing_recipe": {
                "ResultName": name,
                "Grimoire": "Soul Burst",
                "Focus": "Damage Shield",
                "Signature": "Lingering Torment",
                "Affix": "Courage",
            },
        }
    )
    return skill


def test_raw_crafted_skill_stays_out_of_active_bar_choices():
    assert is_player_active(_raw_crafted()) is False


def test_configured_scribed_recipe_is_player_active():
    assert is_player_active(_configured("Warding Burst", -101)) is True


def test_configured_scribed_recipe_appears_in_normal_skill_choices():
    choices = filter_skill_choices(
        [_configured("Warding Burst", -101)],
        character_class="Necromancer",
        slot_index=0,
    )
    assert [skill["name"] for skill in choices] == ["Warding Burst"]


def test_multiple_configured_scribed_skills_do_not_collapse_together():
    choices = filter_skill_choices(
        [
            _configured("Warding Burst", -101),
            _configured("Second Scribed Skill", -102),
        ],
        character_class="Necromancer",
        slot_index=0,
    )
    assert [skill["name"] for skill in choices] == ["Second Scribed Skill", "Warding Burst"]
