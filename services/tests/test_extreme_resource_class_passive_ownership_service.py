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


_CLASS_MASTERY_RESOURCE_IRRELEVANT = {
    ("Class Mastery", "Above and Beyond"),
    ("Class Mastery", "Abyssal Emergence"),
    ("Class Mastery", "An Eye for Exploitation"),
    ("Class Mastery", "Bastion of Light"),
    ("Class Mastery", "Booming Voice"),
    ("Class Mastery", "Bountiful Harvest"),
    ("Class Mastery", "Bright Harbinger"),
    ("Class Mastery", "Calculated Defense"),
    ("Class Mastery", "Conservation of Energy"),
    ("Class Mastery", "Cutthroat's Focus"),
    ("Class Mastery", "Cycle Unending"),
    ("Class Mastery", "Devout Guardian"),
    ("Class Mastery", "Erudite's Rigor"),
    ("Class Mastery", "Fate Realigned"),
    ("Class Mastery", "Font of Power"),
    ("Class Mastery", "Glacial Obstinance"),
    ("Class Mastery", "Green-Keeper's Hide"),
    ("Class Mastery", "Inexorable Descent"),
    ("Class Mastery", "Ink-Scribe's Verve"),
    ("Class Mastery", "Judgment's Brand"),
    ("Class Mastery", "Lead from the Front"),
    ("Class Mastery", "Malevolent Promise"),
    ("Class Mastery", "Nocturnal Inspiration"),
    ("Class Mastery", "Pound of Flesh"),
    ("Class Mastery", "Resolute Defense"),
    ("Class Mastery", "Share the Spoils"),
    ("Class Mastery", "Sphere of Influence"),
    ("Class Mastery", "Static Reverberation"),
    ("Class Mastery", "Steadfast Candescence"),
    ("Class Mastery", "Tundra's Maw"),
    ("Class Mastery", "Unbound Potential"),
    ("Class Mastery", "Veil's Forfeit"),
    ("Class Mastery", "Wild Adaptation"),
    ("Class Mastery", "Wildfire Embers"),
}

_EXPECTED_IDENTITIES = {
    ("Aedric Spear", "Balanced Warrior"),
    ("Aedric Spear", "Burning Light"),
    ("Aedric Spear", "Spear Wall"),
    ("Animal Companions", "Advanced Species"),
    ("Animal Companions", "Bond with Nature"),
    ("Animal Companions", "Flourish"),
    ("Animal Companions", "Savage Beast"),
    ("Ardent Flame", "A Soul Ablaze"),
    ("Ardent Flame", "Combustion"),
    ("Ardent Flame", "Fan the Flames"),
    ("Ardent Flame", "Traumatic Burns"),
    ("Assassination", "Executioner"),
    ("Assassination", "Master Assassin"),
    ("Assassination", "Pressure Points"),
    ("Bone Tyrant", "Death Gleaning"),
    ("Bone Tyrant", "Disdain Harm"),
    ("Bone Tyrant", "Health Avarice"),
    ("Bone Tyrant", "Last Gasp"),
    ("Class Mastery", "Nothing Wasted"),
    ("Curative Runeforms", "Erudition"),
    ("Curative Runeforms", "Healing Tides"),
    ("Curative Runeforms", "Hideous Clarity"),
    ("Curative Runeforms", "Intricate Runeforms"),
    ("Daedric Summoning", "Daedric Protection"),
    ("Daedric Summoning", "Power Stone"),
    ("Daedric Summoning", "Rebate"),
    ("Dark Magic", "Exploitation"),
    ("Dark Magic", "Persistence"),
    ("Dark Magic", "Unholy Knowledge"),
    ("Dawn's Wrath", "Enduring Rays"),
    ("Dawn's Wrath", "Illuminate"),
    ("Dawn's Wrath", "Prism"),
    ("Dawn's Wrath", "Restoring Spirit"),
    ("Draconic Power", "Burnished Scales"),
    ("Draconic Power", "Elder Dragon"),
    ("Draconic Power", "The Storm Voice"),
    ("Draconic Power", "World in Ruin"),
    ("Earthen Heart", "Heart of Stone"),
    ("Earthen Heart", "Landslide"),
    ("Earthen Heart", "Mountain Giant"),
    ("Grave Lord", "Death Knell"),
    ("Grave Lord", "Dismember"),
    ("Grave Lord", "Rapid Rot"),
    ("Grave Lord", "Reusable Parts"),
    ("Herald of the Tome", "Psychic Lesion"),
    ("Restoring Light", "Master Ritualist"),
    ("Restoring Light", "Mending"),
    ("Shadow", "Dark Veil"),
    ("Shadow", "Refreshing Shadows"),
    ("Siphoning", "Magicka Flood"),
    ("Siphoning", "Transfer"),
    ("Soldier of Apocrypha", "Circumvented Fate"),
    ("Storm Calling", "Capacitor"),
    ("Storm Calling", "Energized"),
    ("Storm Calling", "Expert Mage"),
    ("Winter's Embrace", "Frozen Armor"),
    ("Winter's Embrace", "Glacial Presence"),
    ("Winter's Embrace", "Piercing Cold"),
} | _CLASS_MASTERY_RESOURCE_IRRELEVANT


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


def test_reviewed_class_rows_have_objective_specific_resource_status():
    rows = ExtremeResourceClassPassiveOwnershipService.reviewed()
    identities = {(row.skill_line, row.passive_name) for row in rows}
    assert identities == _EXPECTED_IDENTITIES

    expected_accounted = {
        "max_health": {
            ("Bone Tyrant", "Last Gasp"),
            ("Class Mastery", "Nothing Wasted"),
        },
        "max_magicka": {("Siphoning", "Magicka Flood")},
        "max_stamina": {("Siphoning", "Magicka Flood")},
    }

    for objective in ("max_health", "max_magicka", "max_stamina"):
        for line, name in _EXPECTED_IDENTITIES:
            resolution = ExtremeResourceClassPassiveOwnershipService.resolve(
                _passive(name, line),
                objective,
            )
            assert resolution is not None
            row, status = resolution
            assert row.identity == (line, name)
            expected_status = (
                ExtremeResourceClassPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
                if (line, name) in expected_accounted[objective]
                else ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT
            )
            assert status is expected_status


def test_class_mastery_resource_rows_are_irrelevant_to_all_maximum_resource_objectives():
    for objective in ("max_health", "max_magicka", "max_stamina"):
        for line, name in _CLASS_MASTERY_RESOURCE_IRRELEVANT:
            resolution = ExtremeResourceClassPassiveOwnershipService.resolve(
                _passive(name, line),
                objective,
            )
            assert resolution is not None
            row, status = resolution
            assert row.identity == (line, name)
            assert status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_nothing_wasted_is_max_health_only():
    health_resolution = ExtremeResourceClassPassiveOwnershipService.resolve(
        _passive("Nothing Wasted", "Class Mastery"),
        "max_health",
    )
    assert health_resolution is not None
    _, health_status = health_resolution
    assert health_status is ExtremeResourceClassPassiveOwnershipStatus.CANONICALLY_ACCOUNTED

    for objective in ("max_magicka", "max_stamina"):
        resolution = ExtremeResourceClassPassiveOwnershipService.resolve(
            _passive("Nothing Wasted", "Class Mastery"),
            objective,
        )
        assert resolution is not None
        _, status = resolution
        assert status is ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT


def test_class_passive_ownership_requires_exact_skill_line_and_class_domain():
    wrong_line = _passive("Flourish", "Not Animal Companions")
    assert ExtremeResourceClassPassiveOwnershipService.resolve(wrong_line, "max_health") is None

    wrong_draconic_line = _passive("Elder Dragon", "Not Draconic Power")
    assert ExtremeResourceClassPassiveOwnershipService.resolve(wrong_draconic_line, "max_health") is None

    mastery_wrong_line = _passive("Bountiful Harvest", "Not Class Mastery")
    assert (
        ExtremeResourceClassPassiveOwnershipService.resolve(mastery_wrong_line, "max_magicka")
        is None
    )

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


def test_passive_denominator_routes_reviewed_class_rows_by_objective():
    rows = ExtremeResourceClassPassiveOwnershipService.reviewed()
    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = ExtremeResourcePassiveCoverageAuditService(
            universe_service=_Universe(),
            race_repository=_RaceRepository(),
        ).build(objective)

        assert audit.denominator_proven is True
        for row in rows:
            identity = f"[class] {row.skill_line} :: {row.passive_name}"
            status = row.status_for(objective)
            if status is ExtremeResourceClassPassiveOwnershipStatus.CANONICALLY_ACCOUNTED:
                assert identity in audit.accounted_elsewhere
                assert identity not in audit.static_irrelevant
            else:
                assert identity in audit.static_irrelevant
                assert identity not in audit.accounted_elsewhere
            assert identity not in audit.context_required
            assert identity not in audit.unresolved

        assert "[class] Not Animal Companions :: Flourish" in audit.context_required
        assert "[class] Not Draconic Power :: Elder Dragon" in audit.unresolved
