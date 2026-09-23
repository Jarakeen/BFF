from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.extreme_sustained_dps_weapon_ability_enchantment_occurrence_classifier import (
    ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)


class _Coefficients:
    def __init__(self, *, skill_rank_id=42, unresolved=()):
        self.skill_rank_id = skill_rank_id
        self.unresolved = tuple(unresolved)

    def resolve_entity_id(self, _name):
        skill = (
            None
            if self.skill_rank_id is None
            else SimpleNamespace(skill_rank_id=int(self.skill_rank_id))
        )
        return SimpleNamespace(rank=skill, unresolved=self.unresolved)


class _Components:
    def __init__(self, rows):
        self.rows = dict(rows)

    def get_component(self, skill_rank_id, coefficient_number):
        return self.rows.get((int(skill_rank_id), int(coefficient_number)))


def _component(*, is_dot, is_aoe, is_damage=True):
    return SimpleNamespace(
        is_damage=bool(is_damage),
        is_dot=is_dot,
        is_aoe=is_aoe,
    )


def _action():
    return RotationAction(
        1.0,
        0,
        RotationActionKind.SKILL,
        "Weapon Skill",
        "back",
    )


def _occurrence(time_seconds, coefficient_number):
    return RotationActionDamageOccurrence(
        time_seconds=float(time_seconds),
        sequence=0,
        damage_value=100.0,
        source_name="Weapon Skill",
        coefficient_number=coefficient_number,
    )


def _evidence(*rows):
    return RotationActionDamageOccurrenceEvidence(
        action_time_seconds=1.0,
        action_sequence=0,
        occurrences=tuple(rows),
    )


def test_classifier_keeps_direct_and_area_dot_but_excludes_single_target_dot():
    direct = _occurrence(1.0, 1)
    single_target_dot = _occurrence(2.0, 2)
    area_dot = _occurrence(3.0, 3)
    service = ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier(
        coefficient_repository=_Coefficients(),
        component_repository=_Components(
            {
                (42, 1): _component(is_dot=False, is_aoe=False),
                (42, 2): _component(is_dot=True, is_aoe=False),
                (42, 3): _component(is_dot=True, is_aoe=True),
            }
        ),
    )

    result = service.resolve(
        candidate=object(),
        action=_action(),
        occurrence_evidence=_evidence(direct, single_target_dot, area_dot),
    )

    assert result.unresolved == ()
    assert result.occurrences == (direct, area_dot)
    assert any("Excluded single-target DoT occurrences: 1" in row for row in result.evidence)


def test_classifier_fails_closed_when_component_shape_is_incomplete():
    service = ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier(
        coefficient_repository=_Coefficients(),
        component_repository=_Components(
            {(42, 1): _component(is_dot=True, is_aoe=None)}
        ),
    )

    result = service.resolve(
        candidate=object(),
        action=_action(),
        occurrence_evidence=_evidence(_occurrence(2.0, 1)),
    )

    assert result.occurrences == ()
    assert any("reviewed DoT and AoE identity" in row for row in result.unresolved)


def test_classifier_fails_closed_when_occurrence_has_no_coefficient_identity():
    occurrence = RotationActionDamageOccurrence(
        time_seconds=1.0,
        sequence=0,
        damage_value=100.0,
        source_name="Weapon Skill",
    )
    service = ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier(
        coefficient_repository=_Coefficients(),
        component_repository=_Components({}),
    )

    result = service.resolve(
        candidate=object(),
        action=_action(),
        occurrence_evidence=_evidence(occurrence),
    )

    assert result.occurrences == ()
    assert any("lacks coefficient identity" in row for row in result.unresolved)


def test_classifier_fails_closed_when_skill_rank_resolution_is_unresolved():
    service = ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier(
        coefficient_repository=_Coefficients(
            skill_rank_id=None,
            unresolved=("ambiguous canonical skill rank",),
        ),
        component_repository=_Components({}),
    )

    result = service.resolve(
        candidate=object(),
        action=_action(),
        occurrence_evidence=_evidence(_occurrence(1.0, 1)),
    )

    assert result.occurrences == ()
    assert result.unresolved == ("ambiguous canonical skill rank",)


def test_classifier_rejects_damage_occurrence_that_maps_to_non_damage_component():
    service = ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier(
        coefficient_repository=_Coefficients(),
        component_repository=_Components(
            {(42, 1): _component(is_dot=False, is_aoe=False, is_damage=False)}
        ),
    )

    result = service.resolve(
        candidate=object(),
        action=_action(),
        occurrence_evidence=_evidence(_occurrence(1.0, 1)),
    )

    assert result.occurrences == ()
    assert any("non-damage component classification" in row for row in result.unresolved)
