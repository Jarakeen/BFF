from types import SimpleNamespace

from minmax.skill_component_classification import (
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingResolution,
)
from services.rotation_healer_saved_build_periodic_timing_service import (
    RotationHealerSavedBuildPeriodicTimingService,
)


class _Coefficients:
    def __init__(self, ranks):
        self.ranks = ranks

    def resolve_name(self, name):
        rank_id = self.ranks.get(name)
        if rank_id is None:
            return SimpleNamespace(rank=None, unresolved=("skill unresolved",))
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=rank_id),
            unresolved=(),
        )


class _Components:
    def __init__(self, rows):
        self.rows = rows

    def get_for_skill_rank(self, rank_id):
        return tuple(self.rows.get(rank_id, ()))


class _Timing:
    def __init__(self, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve(self, *, source_name, coefficient_number):
        self.calls.append((source_name, coefficient_number))
        return RotationHealerCanonicalPeriodicTimingResolution(
            source_name=source_name,
            coefficient_number=coefficient_number,
            skill_rank_id=10,
            ability_id=20,
            component_fragment="healed every 1 second",
            timing=None,
            duration_seconds=6.0,
            unresolved=self.unresolved,
        )


def _build(front=(), back=()):
    return PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        FrontBarSkills=list(front),
        BackBarSkills=list(back),
    )


def _service(*, ranks, rows, timing=None):
    return RotationHealerSavedBuildPeriodicTimingService(
        "unused.db",
        coefficient_repository=_Coefficients(ranks),
        component_repository=_Components(rows),
        timing_service=timing or _Timing(),
    )


def test_discovers_periodic_heal_on_exact_saved_bar_and_slot():
    timing = _Timing()
    service = _service(
        ranks={"Budding Seeds": 10, "Combat Prayer": 11},
        rows={
            10: (
                SkillComponentClassification(
                    skill_rank_id=10,
                    coefficient_number=2,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=True,
                ),
            ),
            11: (
                SkillComponentClassification(
                    skill_rank_id=11,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=False,
                ),
            ),
        },
        timing=timing,
    )

    report = service.inspect(_build(front=("Combat Prayer", "Budding Seeds")))

    assert [(item.bar, item.slot, item.skill_name, item.coefficient_number) for item in report.entries] == [
        ("front", 2, "Budding Seeds", 2)
    ]
    assert timing.calls == [("Budding Seeds", 2)]
    assert report.character_name == "Magrat"
    assert report.build_name == "DF Healer"
    assert report.unresolved == ()


def test_reviewed_periodic_heal_temporal_scope_is_sufficient_without_legacy_is_dot():
    service = _service(
        ranks={"Illustrious Healing": 12},
        rows={
            12: (
                SkillComponentClassification(
                    skill_rank_id=12,
                    coefficient_number=3,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=None,
                    heal_temporal_scope=HealTemporalScope.PERIODIC,
                ),
            ),
        },
    )

    report = service.inspect(_build(back=("Illustrious Healing",)))
    assert len(report.entries) == 1
    assert report.entries[0].bar == "back"
    assert report.entries[0].slot == 1


def test_direct_heal_and_damage_components_do_not_enter_periodic_heal_report():
    service = _service(
        ranks={"Mixed Skill": 13},
        rows={
            13: (
                SkillComponentClassification(
                    skill_rank_id=13,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=False,
                ),
                SkillComponentClassification(
                    skill_rank_id=13,
                    coefficient_number=2,
                    effect_kind=SkillEffectKind.DAMAGE,
                    is_dot=True,
                ),
            ),
        },
    )

    report = service.inspect(_build(front=("Mixed Skill",)))
    assert report.entries == ()
    assert report.unresolved == ()


def test_unresolved_slotted_skill_is_reported_with_bar_and_slot_context():
    service = _service(ranks={}, rows={})
    report = service.inspect(_build(back=("Unknown Heal",)))

    assert report.entries == ()
    assert report.unresolved == (
        "back slot 1 Unknown Heal: skill unresolved",
    )


def test_periodic_timing_gap_is_preserved_without_dropping_component_identity():
    timing = _Timing(unresolved=("first tick timing unresolved",))
    service = _service(
        ranks={"Budding Seeds": 10},
        rows={
            10: (
                SkillComponentClassification(
                    skill_rank_id=10,
                    coefficient_number=2,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=True,
                ),
            ),
        },
        timing=timing,
    )

    report = service.inspect(_build(front=("Budding Seeds",)))

    assert len(report.entries) == 1
    assert report.entries[0].skill_name == "Budding Seeds"
    assert report.unresolved == (
        "front slot 1 Budding Seeds coefficient 2: first tick timing unresolved",
    )


def test_same_periodic_heal_on_both_bars_preserves_both_saved_locations():
    service = _service(
        ranks={"Budding Seeds": 10},
        rows={
            10: (
                SkillComponentClassification(
                    skill_rank_id=10,
                    coefficient_number=2,
                    effect_kind=SkillEffectKind.HEAL,
                    is_dot=True,
                ),
            ),
        },
    )

    report = service.inspect(
        _build(front=("Budding Seeds",), back=("Budding Seeds",))
    )
    assert [(item.bar, item.slot) for item in report.entries] == [
        ("front", 1),
        ("back", 1),
    ]
