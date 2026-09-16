from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from services.extreme_actual_heal_candidate_scope_service import (
    ExtremeActualHealCandidateScopeService,
)
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidate


class _ComponentRepository:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, skill_rank_id):
        return self.rows


def _component(number: int, *, kind=SkillEffectKind.HEAL, aoe=None):
    return SkillComponentClassification(
        skill_rank_id=1,
        coefficient_number=number,
        effect_kind=kind,
        is_aoe=aoe,
    )


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


def test_canonical_heal_components_resolve_aoe_when_all_agree_true() -> None:
    service = ExtremeActualHealCandidateScopeService(
        component_repository=_ComponentRepository((_component(1, aoe=True), _component(2, aoe=True)))
    )

    area, evidence = service._canonical_aoe_for_rank(1, "Area Heal")

    assert area is True
    assert "coef1=True" in str(evidence)
    assert "coef2=True" in str(evidence)


def test_canonical_heal_components_resolve_non_aoe_when_all_agree_false() -> None:
    service = ExtremeActualHealCandidateScopeService(
        component_repository=_ComponentRepository((_component(1, aoe=False),))
    )

    area, evidence = service._canonical_aoe_for_rank(1, "Single Heal")

    assert area is False
    assert "coef1=False" in str(evidence)


def test_incomplete_or_conflicting_heal_component_aoe_stays_unresolved() -> None:
    incomplete = ExtremeActualHealCandidateScopeService(
        component_repository=_ComponentRepository((_component(1, aoe=True), _component(2, aoe=None)))
    )
    conflicting = ExtremeActualHealCandidateScopeService(
        component_repository=_ComponentRepository((_component(1, aoe=True), _component(2, aoe=False)))
    )

    incomplete_area, incomplete_evidence = incomplete._canonical_aoe_for_rank(1, "Mixed Heal")
    conflicting_area, conflicting_evidence = conflicting._canonical_aoe_for_rank(1, "Mixed Heal")

    assert incomplete_area is None
    assert "incomplete" in str(incomplete_evidence)
    assert conflicting_area is None
    assert "conflicts" in str(conflicting_evidence)


def test_non_heal_component_does_not_contaminate_heal_aoe_scope() -> None:
    service = ExtremeActualHealCandidateScopeService(
        component_repository=_ComponentRepository(
            (
                _component(1, aoe=True),
                _component(2, kind=SkillEffectKind.DAMAGE, aoe=False),
            )
        )
    )

    area, _ = service._canonical_aoe_for_rank(1, "Heal With Damage Rider")

    assert area is True
