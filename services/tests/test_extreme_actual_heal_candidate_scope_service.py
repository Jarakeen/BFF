from services.extreme_actual_heal_candidate_scope_service import (
    ExtremeActualHealCandidateScopeService,
)
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidate


def _candidate(*, name: str = "Heal", skill_line: str, class_type: str = ""):
    return ExtremeHealSkillCandidate(
        entity_id="ability:test",
        name=name,
        skill_rank_id=1,
        ability_id=2,
        rank=4,
        morph=1,
        skill_line=skill_line,
        class_type=class_type,
        heal_component_count=1,
        can_crit=True,
        legal=True,
        blockers=(),
    )


def test_restoration_staff_heal_is_weapon_and_restoration_scope() -> None:
    result = ExtremeActualHealCandidateScopeService.resolve(
        _candidate(name="Combat Prayer", skill_line="Restoration Staff")
    )

    assert result.is_class_ability is False
    assert result.is_weapon_skill_ability is True
    assert result.is_restoration_staff_ability is True
    assert result.is_area_of_effect is None
    assert result.unresolved


def test_class_heal_is_class_scope_not_weapon_scope() -> None:
    result = ExtremeActualHealCandidateScopeService.resolve(
        _candidate(name="Class Heal", skill_line="Green Balance", class_type="Warden")
    )

    assert result.is_class_ability is True
    assert result.is_weapon_skill_ability is False
    assert result.is_restoration_staff_ability is False


def test_explicit_area_evidence_resolves_aoe_identity() -> None:
    result = ExtremeActualHealCandidateScopeService.resolve(
        _candidate(name="Area Heal", skill_line="Restoration Staff"),
        area_of_effect=True,
        area_evidence="canonical ability shape: radius=8m",
    )

    assert result.is_area_of_effect is True
    assert result.unresolved == ()
    assert any("radius=8m" in item for item in result.evidence)


def test_non_area_evidence_can_explicitly_resolve_false() -> None:
    result = ExtremeActualHealCandidateScopeService.resolve(
        _candidate(name="Single Target Heal", skill_line="Restoration Staff"),
        area_of_effect=False,
        area_evidence="canonical ability shape: single target",
    )

    assert result.is_area_of_effect is False
    assert result.unresolved == ()
