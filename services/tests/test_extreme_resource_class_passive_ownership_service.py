from services.extreme_resource_class_passive_ownership_service import (
    ExtremeResourceClassPassiveOwnershipService,
    ExtremeResourceClassPassiveOwnershipStatus,
)
from services.extreme_resource_passive_coverage_audit_service import (
    ExtremeResourcePassiveCoverageAuditService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(name: str, line: str, description: str = "Reviewed class mechanic."):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Test Class",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description=description,
        domain=ExtremeSkillDomain.CLASS,
    )


_EXPECTED_IDENTITIES = {
    ("Aedric Spear", "Balanced Warrior"),
    ("Aedric Spear", "Spear Wall"),
    ("Animal Companions", "Advanced Species"),
    ("Animal Companions", "Bond with Nature"),
    ("Animal Companions", "Flourish"),
    ("Animal Companions", "Savage Beast"),
    ("Ardent Flame", "A Soul Ablaze"),
    ("Ardent Flame", "Fan the Flames"),
    ("Ardent Flame", "Traumatic Burns"),
    ("Assassination", "Master Assassin"),
    ("Bone Tyrant", "Health Avarice"),
    ("Curative Runeforms", "Erudition"),
    ("Curative Runeforms", "Intricate Runeforms"),
    ("Daedric Summoning", "Rebate"),
    ("Dark Magic", "Unholy Knowledge"),
    ("Dawn's Wrath", "Enduring Rays"),
    ("Dawn's Wrath", "Illuminate"),
    ("Dawn's Wrath", "Prism"),
    ("Dawn's Wrath", "Restoring Spirit"),
    ("Draconic Power", "Burnished Scales"),
    ("Draconic Power", "Elder Dragon"),
    ("Draconic Power", "World in Ruin"),
    ("Grave Lord", "Death Knell"),
    ("Grave Lord", "Rapid Rot"),
    ("Herald of the Tome", "Psychic Lesion"),
    ("Shadow", "Dark Veil"),
    ("Shadow", "Refreshing Shadows"),
    ("Soldier of Apocrypha", "Circumvented Fate"),
    ("Storm Calling", "Expert Mage"),
    ("Winter's Embrace", "Frozen Armor"),
}


class _Universe:
    def passives(self):
        reviewed = tuple(
            _passive(name, line)
            for line, name in sorted(
                _EXPECTED_IDENTITIES,
                key=lambda row: (row[0].casefold(), row[1].casefold()),
            )
        )
        return reviewed + (
            _passive("Flourish", "Not Animal Companions"),
            _passive("Elder Dragon", "Not Draconic Power"),
        )


class _RaceRepository:
    @staticmethod
    def get_stat_map_by_name(_name):
        return {}


def test_reviewed_class_rows_are_proven_irrelevant_to_all_max_resources():
    rows = ExtremeResourceClassPassiveOwnershipService.reviewed()
    identities = {(row.skill_line, row.passive_name) for row in rows}
    assert identities == _EXPECTED_IDENTITIES
    assert all(
        row.status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT
        for row in rows
    )

    for objective in ("max_health", "max_magicka", "max_stamina"):
        for line, name in _EXPECTED_IDENTITIES:
            row = ExtremeResourceClassPassiveOwnershipService.resolve(
                _passive(name, line),
                objective,
            )
            assert row is not None
            assert row.status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_class_passive_ownership_requires_exact_skill_line_and_class_domain():
    wrong_line = _passive("Flourish", "Not Animal Companions")
    assert ExtremeResourceClassPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    wrong_draconic_line = _passive("Elder Dragon", "Not Draconic Power")
    assert ExtremeResourceClassPassiveOwnershipService.resolve(wrong_draconic_line, "max_health") is None

    guild_copy = ExtremePlayerSkillRecord(
        skill_id=2,
        name="Flourish",
        class_type="",
        skill_line="Animal Companions",
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=None,
        max_rank=2,
        max_rank_ability_id=None,
        description="Same words, wrong domain.",
        domain=ExtremeSkillDomain.GUILD,
    )
    assert ExtremeResourceClassPassiveOwnershipService.resolve(guild_copy, "max_health") is None


def test_passive_denominator_moves_reviewed_class_rows_to_static_irrelevant():
    expected_identities = tuple(
        f"[class] {line} :: {name}"
        for line, name in _EXPECTED_IDENTITIES
    )
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for identity in expected_identities:
            assert identity in audit.static_irrelevant
            assert identity not in audit.context_required
            assert identity not in audit.unresolved

        assert "[class] Not Animal Companions :: Flourish" in audit.context_required
        assert "[class] Not Draconic Power :: Elder Dragon" in audit.unresolved
