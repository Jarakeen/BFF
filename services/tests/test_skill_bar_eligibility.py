from services.skill_bar_eligibility import filter_skill_choices, is_eligible, validate_bar


def skill(name, *, line="Two Handed", class_type="", passive=0, player=1, crafted=0, ultimate=False, base=1, morph=0):
    return {
        "name": name,
        "skill_line": line,
        "class_type": class_type,
        "is_passive": passive,
        "is_player": player,
        "is_crafted": crafted,
        "base_mechanic": 8 if ultimate else 1,
        "base_ability_id": base,
        "ability_id": base * 10 + morph,
        "morph": morph,
        "rank": 1,
    }


def test_active_slots_reject_ultimate_and_passive():
    assert not is_eligible(skill("Horn", ultimate=True), character_class="Warden", slot_index=0)
    assert not is_eligible(skill("Passive", passive=1), character_class="Warden", slot_index=0)


def test_ultimate_slot_accepts_valid_class_ultimate():
    ultimate = skill("Warden Ultimate", line="Winter's Embrace", class_type="Warden", ultimate=True)
    assert is_eligible(ultimate, character_class="Warden", slot_index=5)


def test_ultimate_slot_rejects_non_ultimate():
    assert not is_eligible(skill("Vigor"), character_class="Warden", slot_index=5)


def test_other_class_skills_are_rejected():
    arcanist = skill("Arcanist", line="Herald of the Tome", class_type="Arcanist")
    assert not is_eligible(arcanist, character_class="Warden", slot_index=0)


def test_non_combat_lines_are_rejected():
    for line in ("Crafting", "Racial", "Thieves Guild", "Dark Brotherhood", "Excavation", "Legerdemain", "Scrying"):
        assert not is_eligible(skill(line, line=line), character_class="Warden", slot_index=0)


def test_morphs_are_not_collapsed_by_name_or_base_ability():
    choices = filter_skill_choices(
        [
            skill("Base Skill", base=100, morph=0),
            skill("Morph One", base=100, morph=1),
            skill("Morph Two", base=100, morph=2),
        ],
        character_class="Warden",
        slot_index=0,
    )
    assert {item["name"] for item in choices} == {"Base Skill", "Morph One", "Morph Two"}


def test_vampire_and_werewolf_are_mutually_exclusive():
    assert not is_eligible(skill("Vamp", line="Vampire"), character_class="Warden", slot_index=0, vampire=True, werewolf=True)
    assert validate_bar([None] * 6, character_class="Warden", vampire=True, werewolf=True) == [
        "A character cannot be both Vampire and Werewolf."
    ]


def test_vampire_active_requires_vampire_form():
    vamp = skill("Vampire Active", line="Vampire")
    assert not is_eligible(vamp, character_class="Warden", slot_index=0, vampire=True)
    assert is_eligible(vamp, character_class="Warden", slot_index=0, vampire=True, transformed_form="vampire")
    assert not is_eligible(vamp, character_class="Warden", slot_index=0, werewolf=True, transformed_form="werewolf")
