from __future__ import annotations

from services.extreme_player_skill_candidate_service import (
    ExtremePlayerSkillCandidateService,
    ExtremePlayerSkillLegalityContext,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _active(
    name: str,
    line: str,
    domain: ExtremeSkillDomain,
    *,
    class_type: str = "",
    ability_id: int = 100,
    is_crafted: bool = False,
    skill_type: str = "Active",
):
    return ExtremePlayerSkillRecord(
        skill_id=ability_id,
        name=name,
        class_type=class_type,
        skill_line=line,
        skill_type=skill_type,
        is_passive=False,
        is_player=True,
        is_crafted=is_crafted,
        base_ability_id=ability_id,
        max_rank=4,
        max_rank_ability_id=ability_id,
        description="",
        domain=domain,
    )


def _service(rows):
    service = ExtremePlayerSkillCandidateService.__new__(ExtremePlayerSkillCandidateService)

    class FakeUniverse:
        def actives(self):
            return tuple(rows)

    service.universe = FakeUniverse()
    return service


def test_equipped_subclass_lines_and_shared_combat_lines_are_all_candidates():
    rows = (
        _active("Warden Skill", "Winter's Embrace", ExtremeSkillDomain.CLASS, class_type="Warden", ability_id=1),
        _active("Sorc Skill", "Daedric Summoning", ExtremeSkillDomain.CLASS, class_type="Sorcerer", ability_id=2),
        _active("Wall", "Destruction Staff", ExtremeSkillDomain.WEAPON, ability_id=3),
        _active("Prayer", "Restoration Staff", ExtremeSkillDomain.WEAPON, ability_id=4),
        _active("Guild Skill", "Fighters Guild", ExtremeSkillDomain.GUILD, ability_id=5),
        _active("Support Skill", "Support", ExtremeSkillDomain.ALLIANCE_WAR, ability_id=6),
        _active("Soul Skill", "Soul Magic", ExtremeSkillDomain.WORLD, ability_id=7),
    )
    context = ExtremePlayerSkillLegalityContext(
        equipped_class_lines=("Winter's Embrace", "Daedric Summoning", "Green Balance"),
        equipped_weapon_lines=("Restoration Staff",),
    )

    names = {row.name for row in _service(rows).candidates(context)}

    assert "Warden Skill" in names
    assert "Sorc Skill" in names
    assert "Prayer" in names
    assert "Guild Skill" in names
    assert "Support Skill" in names
    assert "Soul Skill" in names
    assert "Wall" not in names


def test_class_skill_outside_equipped_subclass_lines_is_illegal():
    row = _active(
        "Other Class Skill",
        "Ardent Flame",
        ExtremeSkillDomain.CLASS,
        class_type="Dragonknight",
    )
    context = ExtremePlayerSkillLegalityContext(
        equipped_class_lines=("Winter's Embrace", "Green Balance", "Animal Companions"),
    )

    assert _service((row,)).candidates(context) == ()


def test_vampire_and_werewolf_require_matching_legal_state():
    vampire = _active("Vamp Skill", "Vampire", ExtremeSkillDomain.WORLD, ability_id=10)
    werewolf = _active("Wolf Skill", "Werewolf", ExtremeSkillDomain.WORLD, ability_id=11)
    service = _service((vampire, werewolf))

    mortal = ExtremePlayerSkillLegalityContext(equipped_class_lines=("Green Balance",))
    vamp = ExtremePlayerSkillLegalityContext(
        equipped_class_lines=("Green Balance",),
        vampire=True,
        transformed_form="Vampire",
    )

    assert service.candidates(mortal) == ()
    assert {row.name for row in service.candidates(vamp)} == {"Vamp Skill"}


def test_player_route_cannot_be_both_vampire_and_werewolf():
    try:
        ExtremePlayerSkillLegalityContext(
            equipped_class_lines=("Green Balance",),
            vampire=True,
            werewolf=True,
        )
    except ValueError as exc:
        assert "both Vampire and Werewolf" in str(exc)
    else:
        raise AssertionError("mutually exclusive transformation states must fail")


def test_crafted_skill_requires_exact_configured_ability_identity():
    crafted = _active(
        "Configured Scribed Skill",
        "Restoration Staff",
        ExtremeSkillDomain.WEAPON,
        ability_id=50,
        is_crafted=True,
    )
    service = _service((crafted,))
    denied = ExtremePlayerSkillLegalityContext(
        equipped_class_lines=("Green Balance",),
        equipped_weapon_lines=("Restoration Staff",),
    )
    allowed = ExtremePlayerSkillLegalityContext(
        equipped_class_lines=("Green Balance",),
        equipped_weapon_lines=("Restoration Staff",),
        allowed_scribed_ability_ids=(50,),
    )

    assert service.candidates(denied) == ()
    assert service.candidates(allowed) == (crafted,)


def test_noncombat_crafting_and_utility_actives_never_enter_combat_bar_pool():
    craft = _active("Craft Thing", "Alchemy", ExtremeSkillDomain.CRAFT, ability_id=60)
    utility = _active("Utility Thing", "Scrying", ExtremeSkillDomain.UTILITY, ability_id=61)
    context = ExtremePlayerSkillLegalityContext(equipped_class_lines=("Green Balance",))

    assert _service((craft, utility)).candidates(context) == ()
