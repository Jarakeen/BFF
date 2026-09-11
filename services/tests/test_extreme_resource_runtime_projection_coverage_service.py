from types import SimpleNamespace

from services.extreme_resource_runtime_projection_coverage_service import (
    ExtremeResourceRuntimeProjectionCoverageService,
)


class _AuditService:
    def __init__(self, *, markers, denominator_proven=True, unresolved=()):
        self.markers = tuple(markers)
        self.denominator_proven = denominator_proven
        self.unresolved = tuple(unresolved)

    def build(self, objective_key):
        return SimpleNamespace(
            objective_key=objective_key,
            condition_markers=self.markers,
            denominator_proven=self.denominator_proven,
            unresolved=self.unresolved,
        )


class _SkillCatalogService:
    def __init__(self, *, denominator_proven=True, unresolved=()):
        self.denominator_proven = denominator_proven
        self.unresolved = tuple(unresolved)

    def build(self):
        return SimpleNamespace(
            denominator_proven=self.denominator_proven,
            unresolved=self.unresolved,
        )


def _service(*, markers, runtime_proven=True, skill_proven=True):
    return ExtremeResourceRuntimeProjectionCoverageService(
        runtime_audit_service=_AuditService(
            markers=markers,
            denominator_proven=runtime_proven,
        ),
        skill_witness_catalog_service=_SkillCatalogService(
            denominator_proven=skill_proven,
            unresolved=("skill witness gap",) if not skill_proven else (),
        ),
    )


def test_projection_closes_when_every_discovered_runtime_marker_has_execution_owner():
    result = _service(
        markers=(
            "armor_ability_slotted",
            "escalating_fete_stacks:30",
            "food_buff_active",
            "transformed",
        )
    ).build("max_health")

    assert result.projection_complete is True
    assert result.runtime_denominator_proven is True
    assert result.skill_witness_denominator_proven is True
    assert result.instantaneous_self_snapshot is True
    assert result.execution_owned_markers == result.condition_markers
    assert result.unresolved == ()


def test_projection_fails_closed_for_new_unowned_runtime_marker():
    result = _service(
        markers=("drink_buff_active", "some_future_runtime_condition"),
    ).build("max_magicka")

    assert result.projection_complete is False
    assert result.execution_owned_markers == ("drink_buff_active",)
    assert any("some_future_runtime_condition" in item for item in result.unresolved)


def test_projection_requires_skill_witness_denominator_when_skill_marker_is_present():
    result = _service(
        markers=("pet_active", "prowlers_talisman_critical_stacks:10"),
        skill_proven=False,
    ).build("max_magicka")

    assert result.projection_complete is False
    assert result.skill_witness_denominator_proven is False
    assert "skill witness gap" in result.unresolved


def test_projection_does_not_require_skill_catalog_for_non_skill_runtime_markers():
    result = _service(
        markers=("drink_buff_active", "escalating_fete_stacks:30"),
        skill_proven=False,
    ).build("max_stamina")

    assert result.projection_complete is True
    assert result.skill_witness_denominator_proven is True
