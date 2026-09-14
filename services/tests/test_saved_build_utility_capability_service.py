from types import SimpleNamespace

from engine.config import DEFAULT_DATABASE
from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from models.build_model import PlayerBuild
from services.encounter_requirement_evaluation import CapabilityAssessment
from services.saved_build_utility_capability_service import (
    SavedBuildUtilityCapabilityService,
)


class _Coefficients:
    def __init__(self, rows):
        self.rows = dict(rows)

    def resolve_name(self, name):
        return self.rows[name]


class _Utility:
    def __init__(self, rows):
        self.rows = dict(rows)

    def resolve(self, skill_rank_id, coefficient_number):
        return self.rows.get((skill_rank_id, coefficient_number), ())


def _rank(skill_rank_id=10, coefficients=(1,)):
    return SimpleNamespace(
        skill_rank_id=skill_rank_id,
        coefficients=tuple(SimpleNamespace(coefficient_number=value) for value in coefficients),
    )


def _effect(effect_type):
    return SimpleNamespace(effect_type=effect_type)


def _build(*, front=(), back=()):
    build = PlayerBuild(Name="Tank A", BuildName="MT", Role="Tank")
    build.FrontBarSkills = list(front)
    build.BackBarSkills = list(back)
    return build


def test_slotted_canonical_taunt_utility_is_supported():
    service = SavedBuildUtilityCapabilityService(
        "eso.db",
        coefficient_repository=_Coefficients(
            {"Pierce Armor": SimpleNamespace(rank=_rank(), unresolved=())}
        ),
        utility_repository=_Utility(
            {(10, 1): (_effect(SkillComponentUtilityEffectType.TAUNT),)}
        ),
    )

    result = service.evidence_for(
        build=_build(front=("Pierce Armor",)),
        capability_types=("taunt",),
    )[0]

    assert result.assessment is CapabilityAssessment.SUPPORTED
    assert result.member_id == "Tank A"
    assert result.capability_type == "taunt"
    assert "Pierce Armor (front)" in result.source


def test_all_resolved_slotted_skills_without_taunt_are_unsupported():
    service = SavedBuildUtilityCapabilityService(
        "eso.db",
        coefficient_repository=_Coefficients(
            {"Defensive Stance": SimpleNamespace(rank=_rank(), unresolved=())}
        ),
        utility_repository=_Utility({}),
    )

    result = service.evidence_for(
        build=_build(front=("Defensive Stance",)),
        capability_types=("taunt",),
    )[0]

    assert result.assessment is CapabilityAssessment.UNSUPPORTED


def test_unresolved_slotted_skill_keeps_missing_taunt_unknown():
    service = SavedBuildUtilityCapabilityService(
        "eso.db",
        coefficient_repository=_Coefficients(
            {"Mystery Skill": SimpleNamespace(rank=None, unresolved=("not resolved",))}
        ),
        utility_repository=_Utility({}),
    )

    result = service.evidence_for(
        build=_build(front=("Mystery Skill",)),
        capability_types=("taunt",),
    )[0]

    assert result.assessment is CapabilityAssessment.UNKNOWN
    assert "Mystery Skill" in result.source


def test_unknown_utility_capability_mapping_stays_unknown():
    service = SavedBuildUtilityCapabilityService(
        "eso.db",
        coefficient_repository=_Coefficients({}),
        utility_repository=_Utility({}),
    )

    result = service.evidence_for(
        build=_build(),
        capability_types=("teleport_boss",),
    )[0]

    assert result.assessment is CapabilityAssessment.UNKNOWN


def test_real_database_pierce_armor_saved_build_proves_taunt_capability():
    assert DEFAULT_DATABASE.is_file(), f"canonical ESO database is missing: {DEFAULT_DATABASE}"
    build = _build(front=("Pierce Armor",))

    result = SavedBuildUtilityCapabilityService(DEFAULT_DATABASE).evidence_for(
        build=build,
        capability_types=("taunt",),
    )[0]

    assert result.assessment is CapabilityAssessment.SUPPORTED, result.source
    assert "Pierce Armor (front)" in result.source
