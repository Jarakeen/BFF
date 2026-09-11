from services.extreme_resource_weapon_passive_ownership_service import (
    ExtremeResourceWeaponPassiveOwnershipService,
    ExtremeResourceWeaponPassiveOwnershipStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str, *, domain=ExtremeSkillDomain.WEAPON):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description="Reviewed weapon passive.",
        domain=domain,
    )


def test_reviewed_weapon_passives_are_proven_irrelevant_to_all_max_resources():
    rows = ExtremeResourceWeaponPassiveOwnershipService.reviewed()
    identities = {(row.skill_line, row.passive_name) for row in rows}

    expected = {
        ("Restoration Staff", "Restoration Master"),
        ("Restoration Staff", "Restoration Expert"),
        ("Restoration Staff", "Essence Drain"),
        ("Restoration Staff", "Cycle of Life"),
        ("Restoration Staff", "Absorb"),
        ("Destruction Staff", "Penetrating Magic"),
        ("Destruction Staff", "Elemental Force"),
        ("Destruction Staff", "Ancient Knowledge"),
        ("Destruction Staff", "Tri Focus"),
        ("Destruction Staff", "Destruction Expert"),
        ("Bow", "Ranger"),
        ("Dual Wield", "Ambidextrous"),
        ("Dual Wield", "Controlled Fury"),
        ("Dual Wield", "Focused Killer"),
        ("Dual Wield", "Ruffian"),
        ("One Hand and Shield", "Battlefield Mobility"),
        ("One Hand and Shield", "Deadly Bash"),
        ("Two Handed", "Balanced Blade"),
        ("Two Handed", "Forceful"),
    }
    assert identities == expected
    assert all(row.status is ExtremeResourceWeaponPassiveOwnershipStatus.PROVEN_IRRELEVANT for row in rows)

    for objective in ("max_health", "max_magicka", "max_stamina"):
        for line, name in expected:
            row = ExtremeResourceWeaponPassiveOwnershipService.resolve(_passive(name, line), objective)
            assert row is not None
            assert row.status is ExtremeResourceWeaponPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_weapon_ownership_requires_exact_line_and_weapon_domain():
    assert ExtremeResourceWeaponPassiveOwnershipService.resolve(
        _passive("Deadly Bash", "Not One Hand and Shield"),
        "max_health",
    ) is None

    guild_copy = _passive(
        "Restoration Master",
        "Restoration Staff",
        domain=ExtremeSkillDomain.GUILD,
    )
    assert ExtremeResourceWeaponPassiveOwnershipService.resolve(guild_copy, "max_health") is None


def test_weapon_ownership_rejects_unreviewed_objective():
    try:
        ExtremeResourceWeaponPassiveOwnershipService.resolve(
            _passive("Deadly Bash", "One Hand and Shield"),
            "bash_damage",
        )
    except KeyError as exc:
        assert "unreviewed Extreme resource weapon-passive objective" in str(exc)
    else:
        raise AssertionError("expected unsupported resource objective to fail closed")
