from types import SimpleNamespace

from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageMagnitudePolicy,
    PeriodicDamageRefreshBoundary,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_dd_periodic_runtime_semantics_gap_audit_service import (
    RotationDDPeriodicRuntimeSemanticsGapAuditService,
)
from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewEntry,
)


class _Coefficients:
    def __init__(self, rows):
        self.rows = dict(rows)
        self.calls = []

    def resolve_entity_id(self, entity_id):
        self.calls.append(entity_id)
        return self.rows[entity_id]


class _Components:
    def __init__(self, rows):
        self.rows = dict(rows)

    def get_for_skill_rank(self, skill_rank_id):
        return self.rows.get(skill_rank_id, ())


class _Registry:
    def __init__(self, semantics=()):
        self.semantics = tuple(semantics)

    def load(self):
        return self.semantics


class _ReviewService:
    def __init__(self, entries=()):
        self.entries = tuple(entries)

    def by_component(self):
        return {
            (entry.skill_entity_id, entry.coefficient_number): entry
            for entry in self.entries
        }


def _resolution(entity_id: str, skill_rank_id: int, unresolved=()):
    return SimpleNamespace(
        rank=SimpleNamespace(entity_id=entity_id, skill_rank_id=skill_rank_id),
        unresolved=tuple(unresolved),
    )


def _component(number: int, *, is_dot, effect_kind=SkillEffectKind.DAMAGE, source="verified"):
    return SkillComponentClassification(
        skill_rank_id=101,
        coefficient_number=number,
        effect_kind=effect_kind,
        damage_type="magical" if effect_kind is SkillEffectKind.DAMAGE else None,
        is_dot=is_dot,
        is_aoe=False,
        can_crit=True,
        source=source,
    )


def _semantic(skill: str, number: int):
    return RotationPeriodicDamageRuntimeSemantics(
        skill_entity_id=skill,
        coefficient_number=number,
        first_tick_offset_seconds=1.0,
        refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
        source="reviewed test evidence",
        magnitude_policy=PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST,
    )


def test_audit_returns_only_verified_dot_components_missing_reviewed_semantics() -> None:
    coefficients = _Coefficients(
        {"wall_of_elements": _resolution("wall_of_elements", 101)}
    )
    service = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        "unused.db",
        coefficient_repository=coefficients,
        component_repository=_Components(
            {
                101: (
                    _component(1, is_dot=True, source="runtime classification"),
                    _component(2, is_dot=False),
                    _component(3, is_dot=False, effect_kind=SkillEffectKind.HEAL),
                )
            }
        ),
        semantics_registry=_Registry(),
        review_service=_ReviewService(),
    )

    result = service.audit(("Wall of Elements", "wall_of_elements"))

    assert coefficients.calls == ["wall_of_elements"]
    assert result.reviewed == ()
    assert result.unresolved == ()
    assert len(result.missing) == 1
    gap = result.missing[0]
    assert gap.skill_entity_id == "wall_of_elements"
    assert gap.skill_rank_id == 101
    assert gap.coefficient_number == 1
    assert gap.classification_source == "runtime classification"
    assert gap.partial_review is None
    assert result.complete is False


def test_audit_build_uses_both_saved_bars_and_dedupes_skill_identity() -> None:
    coefficients = _Coefficients(
        {
            "wall_of_elements": _resolution("wall_of_elements", 101),
            "barbed_trap": _resolution("barbed_trap", 102),
        }
    )
    service = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        "unused.db",
        coefficient_repository=coefficients,
        component_repository=_Components(
            {
                101: (_component(1, is_dot=True),),
                102: (
                    SkillComponentClassification(
                        skill_rank_id=102,
                        coefficient_number=2,
                        effect_kind=SkillEffectKind.DAMAGE,
                        damage_type="physical",
                        is_dot=True,
                        is_aoe=False,
                        can_crit=True,
                        source="verified",
                    ),
                ),
            }
        ),
        semantics_registry=_Registry(),
        review_service=_ReviewService(),
    )
    build = PlayerBuild(
        Name="Parse Cat",
        BuildName="DD",
        Role="DD",
        FrontBarSkills=["Wall of Elements", "Barbed Trap", "", "", "", ""],
        BackBarSkills=["wall_of_elements", "", "", "", "", ""],
    )

    result = service.audit_build(build)

    assert coefficients.calls == ["wall_of_elements", "barbed_trap"]
    assert tuple(
        (item.skill_entity_id, item.coefficient_number) for item in result.missing
    ) == (("wall_of_elements", 1), ("barbed_trap", 2))


def test_audit_separates_reviewed_periodic_semantics_from_missing_queue() -> None:
    reviewed = _semantic("wall_of_elements", 1)
    service = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        "unused.db",
        coefficient_repository=_Coefficients(
            {"wall_of_elements": _resolution("wall_of_elements", 101)}
        ),
        component_repository=_Components(
            {101: (_component(1, is_dot=True), _component(2, is_dot=True))}
        ),
        semantics_registry=_Registry((reviewed,)),
        review_service=_ReviewService(),
    )

    result = service.audit(("wall_of_elements",))

    assert result.reviewed == (reviewed,)
    assert tuple(item.coefficient_number for item in result.missing) == (2,)
    assert result.unresolved == ()


def test_audit_attaches_partial_review_without_promoting_it_to_reviewed() -> None:
    partial = RotationDDPeriodicRuntimeSemanticsReviewEntry(
        skill_entity_id="skeletal_archer",
        coefficient_number=1,
        duration_seconds=20.0,
        reviewed_interval_seconds=2.0,
        successive_hit_multiplier=1.15,
        evidence=("reviewed tooltip cadence and growth",),
    )
    service = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        "unused.db",
        coefficient_repository=_Coefficients(
            {"skeletal_archer": _resolution("skeletal_archer", 101)}
        ),
        component_repository=_Components({101: (_component(1, is_dot=True),)}),
        semantics_registry=_Registry(),
        review_service=_ReviewService((partial,)),
    )

    result = service.audit(("skeletal_archer",))

    assert result.reviewed == ()
    assert len(result.missing) == 1
    assert result.missing[0].partial_review is partial
    assert partial.unresolved_executable_fields == (
        "first_tick_offset_seconds",
        "refresh_boundary",
        "magnitude_policy",
    )


def test_audit_fails_closed_when_damage_periodic_identity_is_unknown() -> None:
    service = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        "unused.db",
        coefficient_repository=_Coefficients(
            {"mystery_skill": _resolution("mystery_skill", 101)}
        ),
        component_repository=_Components(
            {101: (_component(1, is_dot=None),)}
        ),
        semantics_registry=_Registry(),
        review_service=_ReviewService(),
    )

    result = service.audit(("mystery_skill",))

    assert result.missing == ()
    assert result.reviewed == ()
    assert result.unresolved == (
        "mystery_skill: coefficient 1 damage periodic identity is unresolved",
    )


def test_audit_preserves_unresolved_skill_identity_instead_of_guessing() -> None:
    coefficients = _Coefficients(
        {
            "unknown_skill": SimpleNamespace(
                rank=None,
                unresolved=("Ability entity ID not found: unknown_skill",),
            )
        }
    )
    service = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        "unused.db",
        coefficient_repository=coefficients,
        component_repository=_Components({}),
        semantics_registry=_Registry(),
        review_service=_ReviewService(),
    )

    result = service.audit(("Unknown Skill",))

    assert result.missing == ()
    assert result.reviewed == ()
    assert result.unresolved == ("Ability entity ID not found: unknown_skill",)
