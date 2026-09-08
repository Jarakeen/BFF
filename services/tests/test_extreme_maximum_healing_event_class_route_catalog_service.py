from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_maximum_healing_event_class_route_catalog_service import (
    ExtremeMaximumHealingEventClassRouteCatalogService,
)


class _Catalog:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def rank(self, build, **kwargs):
        self.calls.append((build, kwargs))
        return self.result


def _route(lines=("dark_magic", "daedric_summoning", "storm_calling")):
    return SimpleNamespace(equipped_skill_lines=tuple(lines))


def _ordinary_entry(*, name="Matriarch", critical=15000.0, normal=10000.0, complete=True):
    optimization = SimpleNamespace(
        optimized_event=SimpleNamespace(
            critical_heal=critical,
            normal_heal=normal,
        )
    )
    return SimpleNamespace(
        route=_route(),
        candidate=SimpleNamespace(name=name),
        slotted_index=1,
        optimization=optimization,
        mechanic_complete=complete,
        unresolved=() if complete else ("ordinary unresolved",),
    )


def _blood_entry(*, trigger="Dark Exchange", normal=12000.0, complete=True):
    return SimpleNamespace(
        route=_route(),
        trigger=SimpleNamespace(name=trigger),
        slotted_index=2,
        normal_heal=normal,
        mechanic_complete=complete,
        unresolved=() if complete else ("blood unresolved",),
    )


def _result(entries, *, search_scope=(), omitted_scope=()):
    return SimpleNamespace(
        entries=tuple(entries),
        best_scored=None,
        best_complete=None,
        search_scope=tuple(search_scope),
        omitted_scope=tuple(omitted_scope),
    )


def _build():
    return PlayerBuild(Name="Test", BuildName="Unified", EsoClass="sorcerer")


def test_unified_ranking_compares_ordinary_critical_event_against_noncritical_blood_magic():
    ordinary = _Catalog(_result((_ordinary_entry(critical=15000.0),)))
    blood = _Catalog(_result((_blood_entry(normal=12000.0),)))
    service = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=ordinary,
        blood_magic=blood,
    )

    result = service.rank(_build())

    assert len(result.entries) == 2
    assert result.best_scored.source_kind == "ordinary_skill"
    assert result.best_scored.source_name == "Matriarch"
    assert result.best_scored.event_value == 15000.0
    assert result.best_scored.event_kind == "canonical_maximum"
    assert result.best_complete is result.best_scored


def test_blood_magic_can_win_same_maximum_event_objective_without_fake_crit_multiplier():
    ordinary = _Catalog(_result((_ordinary_entry(critical=15000.0),)))
    blood = _Catalog(_result((_blood_entry(normal=18000.0),)))
    result = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=ordinary,
        blood_magic=blood,
    ).rank(_build())

    assert result.best_scored.source_kind == "blood_magic"
    assert result.best_scored.event_value == 18000.0
    assert result.best_scored.event_kind == "normal_noncritical"


def test_unresolved_ordinary_critical_maximum_does_not_fall_back_to_known_normal_heal():
    ordinary = _Catalog(
        _result(
            (
                _ordinary_entry(
                    name="Unknown Crit Heal",
                    critical=None,
                    normal=25000.0,
                    complete=False,
                ),
            )
        )
    )
    blood = _Catalog(_result((_blood_entry(normal=12000.0),)))
    result = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=ordinary,
        blood_magic=blood,
    ).rank(_build())

    unknown = next(entry for entry in result.entries if entry.source_kind == "ordinary_skill")
    assert unknown.event_value is None
    assert unknown.event_kind == "unresolved"
    assert result.best_scored.source_kind == "blood_magic"


def test_unified_catalog_forwards_route_search_arguments_and_removes_only_merged_boundary():
    ordinary = _Catalog(
        _result(
            (_ordinary_entry(),),
            search_scope=("ordinary scope",),
            omitted_scope=("ordinary omission",),
        )
    )
    blood = _Catalog(
        _result(
            (_blood_entry(),),
            search_scope=("blood scope",),
            omitted_scope=(
                "global maximum-event comparison against ordinary-heal candidates",
                "runtime proof that caster is below full Health at trigger time",
            ),
        )
    )
    build = _build()
    result = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=ordinary,
        blood_magic=blood,
    ).rank(
        build,
        active_bar="back",
        max_passes=7,
        include_base_class_changes=True,
    )

    expected = {
        "active_bar": "back",
        "max_passes": 7,
        "include_base_class_changes": True,
    }
    assert ordinary.calls == [(build, expected)]
    assert blood.calls == [(build, expected)]
    assert "ordinary scope" in result.search_scope
    assert "blood scope" in result.search_scope
    assert "ordinary omission" in result.omitted_scope
    assert "runtime proof that caster is below full Health at trigger time" in result.omitted_scope
    assert "global maximum-event comparison against ordinary-heal candidates" not in result.omitted_scope
