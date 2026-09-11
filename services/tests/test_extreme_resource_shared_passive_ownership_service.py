from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_resource_shared_passive_ownership_service import (
    ExtremeResourceSharedPassiveOwnershipService,
    ExtremeResourceSharedPassiveOwnershipStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str, domain: ExtremeSkillDomain):
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
        description="Conditional reviewed mechanic.",
        domain=domain,
    )


_EXPECTED_IDENTITIES = {
    (ExtremeSkillDomain.ALLIANCE_WAR, "Assault", "Combat Frenzy"),
    (ExtremeSkillDomain.ALLIANCE_WAR, "Assault", "Continuous Attack"),
    (ExtremeSkillDomain.ALLIANCE_WAR, "Assault", "Reach"),
    (ExtremeSkillDomain.ALLIANCE_WAR, "Support", "Magicka Aid"),
    (ExtremeSkillDomain.GUILD, "Dark Brotherhood", "Blade of Woe"),
    (ExtremeSkillDomain.GUILD, "Dark Brotherhood", "Padomaic Sprint"),
    (ExtremeSkillDomain.GUILD, "Dark Brotherhood", "Scales of Pitiless Justice"),
    (ExtremeSkillDomain.GUILD, "Dark Brotherhood", "Shadow Rider"),
    (ExtremeSkillDomain.GUILD, "Dark Brotherhood", "Shadowy Supplier"),
    (ExtremeSkillDomain.GUILD, "Dark Brotherhood", "Spectral Assassin"),
    (ExtremeSkillDomain.GUILD, "Fighters Guild", "Banish the Wicked"),
    (ExtremeSkillDomain.GUILD, "Fighters Guild", "Bounty Hunter"),
    (ExtremeSkillDomain.GUILD, "Fighters Guild", "Intimidating Presence"),
    (ExtremeSkillDomain.GUILD, "Fighters Guild", "Skilled Tracker"),
    (ExtremeSkillDomain.GUILD, "Fighters Guild", "Slayer"),
    (ExtremeSkillDomain.GUILD, "Mages Guild", "Everlasting Magic"),
    (ExtremeSkillDomain.GUILD, "Mages Guild", "Mage Adept"),
    (ExtremeSkillDomain.GUILD, "Mages Guild", "Might of the Guild"),
    (ExtremeSkillDomain.GUILD, "Mages Guild", "Persuasive Will"),
    (ExtremeSkillDomain.GUILD, "Psijic Order", "Clairvoyance"),
    (ExtremeSkillDomain.GUILD, "Psijic Order", "Concentrated Barrier"),
    (ExtremeSkillDomain.GUILD, "Psijic Order", "Deliberation"),
    (ExtremeSkillDomain.GUILD, "Psijic Order", "See the Unseen"),
    (ExtremeSkillDomain.GUILD, "Psijic Order", "Spell Orb"),
    (ExtremeSkillDomain.GUILD, "Thieves Guild", "Clemency"),
    (ExtremeSkillDomain.GUILD, "Thieves Guild", "Finders Keepers"),
    (ExtremeSkillDomain.GUILD, "Thieves Guild", "Haggling"),
    (ExtremeSkillDomain.GUILD, "Thieves Guild", "Swiftly Forgotten"),
    (ExtremeSkillDomain.GUILD, "Thieves Guild", "Timely Escape"),
    (ExtremeSkillDomain.GUILD, "Thieves Guild", "Veil of Shadows"),
    (ExtremeSkillDomain.GUILD, "Undaunted", "Undaunted Command"),
    (ExtremeSkillDomain.WEAPON, "One Hand and Shield", "Deflect Bolts"),
    (ExtremeSkillDomain.WEAPON, "One Hand and Shield", "Fortress"),
    (ExtremeSkillDomain.WORLD, "Soul Magic", "Soul Lock"),
    (ExtremeSkillDomain.WORLD, "Soul Magic", "Soul Shatter"),
    (ExtremeSkillDomain.WORLD, "Soul Magic", "Soul Summons"),
    (ExtremeSkillDomain.WORLD, "Vampire", "Blood Ritual"),
    (ExtremeSkillDomain.WORLD, "Vampire", "Dark Stalker"),
    (ExtremeSkillDomain.WORLD, "Vampire", "Feed"),
    (ExtremeSkillDomain.WORLD, "Vampire", "Strike from the Shadows"),
    (ExtremeSkillDomain.WORLD, "Vampire", "Undeath"),
    (ExtremeSkillDomain.WORLD, "Vampire", "Unnatural Movement"),
    (ExtremeSkillDomain.WORLD, "Werewolf", "Blood Rage"),
    (ExtremeSkillDomain.WORLD, "Werewolf", "Call of the Hunt"),
    (ExtremeSkillDomain.WORLD, "Werewolf", "Insatiable Hunger"),
    (ExtremeSkillDomain.WORLD, "Werewolf", "Master of the Chase"),
    (ExtremeSkillDomain.WORLD, "Werewolf", "Shadow of the Bloodmoon"),
}


class _Universe:
    def passives(self):
        reviewed = tuple(
            _passive(name, line, domain)
            for domain, line, name in sorted(
                _EXPECTED_IDENTITIES,
                key=lambda row: (row[0].value, row[1].casefold(), row[2].casefold()),
            )
        )
        return reviewed + (
            _passive("Fortress", "Not One Hand and Shield", ExtremeSkillDomain.WEAPON),
            _passive("Undeath", "Not Vampire", ExtremeSkillDomain.WORLD),
            _passive("Magicka Controller", "Mages Guild", ExtremeSkillDomain.GUILD),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_reviewed_shared_rows_are_proven_irrelevant_to_all_max_resources():
    rows = ExtremeResourceSharedPassiveOwnershipService.reviewed()
    identities = {(row.domain, row.skill_line, row.passive_name) for row in rows}
    assert identities == _EXPECTED_IDENTITIES
    assert all(
        row.status is ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT
        for row in rows
    )

    for objective in ("max_health", "max_magicka", "max_stamina"):
        for domain, line, name in _EXPECTED_IDENTITIES:
            row = ExtremeResourceSharedPassiveOwnershipService.resolve(
                _passive(name, line, domain),
                objective,
            )
            assert row is not None
            assert row.status is ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_shared_ownership_requires_exact_domain_line_and_name():
    wrong_line = _passive("Fortress", "Not One Hand and Shield", ExtremeSkillDomain.WEAPON)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    wrong_domain = _passive("Slayer", "Fighters Guild", ExtremeSkillDomain.WEAPON)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_domain, "max_health") is None

    wrong_assault_line = _passive("Reach", "Support", ExtremeSkillDomain.ALLIANCE_WAR)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_assault_line, "max_health") is None

    wrong_world_line = _passive("Undeath", "Not Vampire", ExtremeSkillDomain.WORLD)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_world_line, "max_health") is None

    wrong_world_domain = _passive("Undeath", "Vampire", ExtremeSkillDomain.GUILD)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(wrong_world_domain, "max_health") is None

    max_resource_guild_passive = _passive("Magicka Controller", "Mages Guild", ExtremeSkillDomain.GUILD)
    assert ExtremeResourceSharedPassiveOwnershipService.resolve(max_resource_guild_passive, "max_magicka") is None


def test_passive_denominator_moves_reviewed_shared_rows_to_static_irrelevant():
    reviewed_identities = tuple(
        f"[{domain.value}] {line} :: {name}"
        for domain, line, name in _EXPECTED_IDENTITIES
    )
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for identity in reviewed_identities:
            assert identity in audit.static_irrelevant
            assert identity not in audit.context_required
            assert identity not in audit.unresolved
        assert "[weapon] Not One Hand and Shield :: Fortress" in audit.unresolved
        assert "[world] Not Vampire :: Undeath" in audit.unresolved

        # Magicka Controller is intentionally not in the shared irrelevance ledger.
        # Its real Max Magicka ownership is reviewed by the contextual active-bar path.
        if objective == "max_magicka":
            assert "[guild] Mages Guild :: Magicka Controller" in audit.accounted_elsewhere
        else:
            assert "[guild] Mages Guild :: Magicka Controller" in audit.context_required
