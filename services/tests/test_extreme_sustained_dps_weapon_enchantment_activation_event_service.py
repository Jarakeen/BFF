from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
    ExtremeSustainedDPSWeaponEnchantmentActivationEventService,
    ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _candidate(*actions):
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=20.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
    )


class _SkillLines:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def skill_line_for_ability_name(self, name):
        return self.mapping.get(name)


class _Occurrences:
    def __init__(self, rows):
        self.rows = dict(rows)

    def evaluate_action_occurrences(self, *, action, **_kwargs):
        key = (float(action.time_seconds), int(action.sequence))
        rows = self.rows.get(key, ())
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=float(action.time_seconds),
            action_sequence=int(action.sequence),
            occurrences=tuple(rows),
            unresolved=(),
        )



class _WeaponAbilityOccurrenceClassifier:
    def __init__(self, *, keep=None, unresolved=()):
        self.keep = keep
        self.unresolved = tuple(unresolved)

    def resolve(self, *, occurrence_evidence, **_kwargs):
        rows = tuple(occurrence_evidence.occurrences)
        if self.keep is not None:
            rows = tuple(row for index, row in enumerate(rows) if index in self.keep)
        return ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences(
            occurrences=rows,
            evidence=("reviewed weapon-ability occurrence eligibility",),
            unresolved=self.unresolved,
        )

def _occurrence(time, sequence, source, damage=100.0):
    return RotationActionDamageOccurrence(
        time_seconds=float(time),
        sequence=int(sequence),
        damage_value=float(damage),
        source_name=source,
    )


def test_landed_light_and_heavy_damage_are_activation_opportunities() -> None:
    light = RotationAction(
        1.0, 0, RotationActionKind.LIGHT_ATTACK, "Light Attack", "front"
    )
    heavy = RotationAction(
        4.0, 0, RotationActionKind.HEAVY_ATTACK, "Heavy Attack", "back"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({}),
    ).resolve(
        candidate=_candidate(light, heavy),
        occurrence_provider=_Occurrences(
            {
                (1.0, 0): (_occurrence(1.0, 0, "Light Attack"),),
                (4.0, 0): (_occurrence(5.2, 0, "Heavy Attack"),),
            }
        ),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert tuple(row.trigger for row in result.events) == (
        WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
        WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
    )
    assert tuple(row.time_seconds for row in result.events) == (1.0, 5.2)
    assert tuple(row.source_bar for row in result.events) == ("front", "back")
    assert all(row.target == "Boss" for row in result.events)


def test_weapon_line_skill_damage_is_eligible_but_class_skill_damage_is_not() -> None:
    wall = RotationAction(
        1.0, 0, RotationActionKind.SKILL, "Wall of Elements", "back"
    )
    class_skill = RotationAction(
        2.0, 0, RotationActionKind.SKILL, "Class Blast", "front"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines(
            {
                "Wall of Elements": "Destruction Staff",
                "Class Blast": "Storm Calling",
            }
        ),
        weapon_ability_occurrence_classifier=_WeaponAbilityOccurrenceClassifier(),
    ).resolve(
        candidate=_candidate(wall, class_skill),
        occurrence_provider=_Occurrences(
            {
                (1.0, 0): (
                    _occurrence(1.0, 0, "Wall of Elements"),
                    _occurrence(2.0, 1, "Wall of Elements"),
                ),
                (2.0, 0): (_occurrence(2.0, 0, "Class Blast"),),
            }
        ),
    )

    assert result.unresolved == ()
    assert tuple(row.source for row in result.events) == (
        "Wall of Elements",
        "Wall of Elements",
    )
    assert tuple(row.source_bar for row in result.events) == ("back", "back")


def test_zero_damage_occurrence_is_not_an_activation_opportunity() -> None:
    light = RotationAction(
        1.0, 0, RotationActionKind.LIGHT_ATTACK, "Light Attack", "front"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({}),
    ).resolve(
        candidate=_candidate(light),
        occurrence_provider=_Occurrences(
            {(1.0, 0): (_occurrence(1.0, 0, "Light Attack", damage=0.0),)}
        ),
    )

    assert result.events == ()
    assert result.unresolved == ()


def test_unclassified_skill_line_fails_closed() -> None:
    skill = RotationAction(
        1.0, 0, RotationActionKind.SKILL, "Mystery Skill", "front"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({}),
    ).resolve(
        candidate=_candidate(skill),
        occurrence_provider=_Occurrences({}),
    )

    assert result.events == ()
    assert any("canonical skill line is unavailable" in row for row in result.unresolved)


def test_missing_occurrence_provider_fails_closed() -> None:
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({}),
    ).resolve(
        candidate=_candidate(),
        occurrence_provider=None,
    )

    assert result.events == ()
    assert any("exact-time damage occurrence evidence" in row for row in result.unresolved)


def test_weapon_line_skill_occurrences_fail_closed_without_eligibility_classifier() -> None:
    skill = RotationAction(
        1.0, 0, RotationActionKind.SKILL, "Poison Injection", "back"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({"Poison Injection": "Bow"}),
    ).resolve(
        candidate=_candidate(skill),
        occurrence_provider=_Occurrences(
            {
                (1.0, 0): (
                    _occurrence(1.0, 0, "Poison Injection direct"),
                    _occurrence(2.0, 1, "Poison Injection DoT"),
                ),
            }
        ),
    )

    assert result.events == ()
    assert any(
        "occurrence-level eligibility classification" in row
        for row in result.unresolved
    )


def test_weapon_ability_occurrence_classifier_can_exclude_single_target_dot_ticks() -> None:
    skill = RotationAction(
        1.0, 0, RotationActionKind.SKILL, "Poison Injection", "back"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({"Poison Injection": "Bow"}),
        weapon_ability_occurrence_classifier=_WeaponAbilityOccurrenceClassifier(
            keep={0},
        ),
    ).resolve(
        candidate=_candidate(skill),
        occurrence_provider=_Occurrences(
            {
                (1.0, 0): (
                    _occurrence(1.0, 0, "Poison Injection direct"),
                    _occurrence(2.0, 1, "Poison Injection DoT"),
                ),
            }
        ),
    )

    assert result.unresolved == ()
    assert tuple(row.source for row in result.events) == (
        "Poison Injection direct",
    )


def test_weapon_ability_occurrence_classifier_blockers_fail_closed() -> None:
    skill = RotationAction(
        1.0, 0, RotationActionKind.SKILL, "Mystery Bow Skill", "back"
    )
    result = ExtremeSustainedDPSWeaponEnchantmentActivationEventService(
        skill_line_repository=_SkillLines({"Mystery Bow Skill": "Bow"}),
        weapon_ability_occurrence_classifier=_WeaponAbilityOccurrenceClassifier(
            unresolved=("component trigger family unresolved",),
        ),
    ).resolve(
        candidate=_candidate(skill),
        occurrence_provider=_Occurrences(
            {(1.0, 0): (_occurrence(1.0, 0, "Mystery Bow Skill"),)}
        ),
    )

    assert result.events == ()
    assert any(
        "component trigger family unresolved" in row
        for row in result.unresolved
    )
