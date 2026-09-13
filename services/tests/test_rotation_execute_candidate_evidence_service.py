from __future__ import annotations

from types import SimpleNamespace

from minmax.skill_component_condition import (
    SkillComponentCondition,
    SkillComponentConditionType,
)
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidenceService,
)


class _Coefficients:
    def __init__(self, resolution):
        self.resolution = resolution
        self.requested = []

    def resolve_name(self, name):
        self.requested.append(name)
        return self.resolution


class _Consequences:
    def __init__(self, by_component):
        self.by_component = dict(by_component)
        self.calls = []

    def resolve(self, skill_rank_id, coefficient_number):
        self.calls.append((skill_rank_id, coefficient_number))
        return tuple(self.by_component.get(coefficient_number, ()))


def _rank(*numbers):
    return SimpleNamespace(
        name="Executioner",
        entity_id="executioner",
        skill_rank_id=42,
        coefficients=tuple(SimpleNamespace(coefficient_number=number) for number in numbers),
    )


def _condition(*, kind=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT, threshold=0.5):
    return SkillComponentCondition(
        skill_rank_id=42,
        coefficient_number=2,
        condition_type=kind,
        threshold=threshold,
        evidence="below 50% target Health",
    )


def _consequence(*, condition, kind=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE):
    return SkillComponentConditionalConsequence(
        skill_rank_id=42,
        coefficient_number=2,
        consequence_type=kind,
        condition=condition,
        maximum_bonus_fraction=4.0 if kind is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE else None,
        evidence="up to 400% more damage",
    )


def test_resolves_explicit_target_health_execute_damage_evidence() -> None:
    resolution = SimpleNamespace(rank=_rank(1, 2), unresolved=())
    coefficients = _Coefficients(resolution)
    consequences = _Consequences(
        {
            2: (
                _consequence(condition=_condition()),
            ),
        }
    )
    service = RotationExecuteCandidateEvidenceService(
        coefficients=coefficients,
        consequences=consequences,
    )

    result = service.resolve("Executioner")

    assert result.requested_skill_name == "Executioner"
    assert result.resolved_skill_name == "Executioner"
    assert result.entity_id == "executioner"
    assert result.has_threshold_execute_evidence is True
    assert len(result.components) == 1
    component = result.components[0]
    assert component.skill_rank_id == 42
    assert component.coefficient_number == 2
    assert component.threshold == 0.5
    assert component.maximum_bonus_fraction == 4.0
    assert component.consequence_type is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE
    assert consequences.calls == [(42, 1), (42, 2)]


def test_self_health_condition_is_not_treated_as_target_execute_evidence() -> None:
    resolution = SimpleNamespace(rank=_rank(2), unresolved=())
    service = RotationExecuteCandidateEvidenceService(
        coefficients=_Coefficients(resolution),
        consequences=_Consequences(
            {
                2: (
                    _consequence(
                        condition=_condition(
                            kind=SkillComponentConditionType.SELF_HEALTH_BELOW_PERCENT
                        )
                    ),
                ),
            }
        ),
    )

    result = service.resolve("Executioner")

    assert result.components == ()
    assert result.has_threshold_execute_evidence is False
    assert result.unresolved == ()


def test_missing_threshold_evidence_is_not_promoted_to_negative_execute_claim() -> None:
    resolution = SimpleNamespace(rank=_rank(1), unresolved=())
    service = RotationExecuteCandidateEvidenceService(
        coefficients=_Coefficients(resolution),
        consequences=_Consequences({}),
    )

    result = service.resolve("Some Skill")

    assert result.resolved_skill_name == "Executioner"
    assert result.components == ()
    assert result.unresolved == ()


def test_unresolved_skill_identity_fails_closed() -> None:
    resolution = SimpleNamespace(
        rank=None,
        unresolved=("Ambiguous skill name 'Mystery Skill'",),
    )
    service = RotationExecuteCandidateEvidenceService(
        coefficients=_Coefficients(resolution),
        consequences=_Consequences({}),
    )

    result = service.resolve("Mystery Skill")

    assert result.resolved_skill_name is None
    assert result.entity_id is None
    assert result.components == ()
    assert result.unresolved == ("Ambiguous skill name 'Mystery Skill'",)


def test_blank_skill_name_fails_closed_without_repository_lookup() -> None:
    coefficients = _Coefficients(SimpleNamespace(rank=None, unresolved=()))
    service = RotationExecuteCandidateEvidenceService(
        coefficients=coefficients,
        consequences=_Consequences({}),
    )

    result = service.resolve("   ")

    assert result.components == ()
    assert result.unresolved == ("skill name is required for execute evidence",)
    assert coefficients.requested == []
