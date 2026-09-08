from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_class_route_catalog_service as module
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_heal_skill_candidate_service import ExtremeHealSkillCandidate


def _candidate(name: str, *, skill_line: str, class_type: str) -> ExtremeHealSkillCandidate:
    token = name.casefold().replace(" ", "_")
    return ExtremeHealSkillCandidate(
        entity_id=token,
        name=name,
        skill_rank_id=1,
        ability_id=1,
        rank=4,
        morph=1,
        skill_line=skill_line,
        class_type=class_type,
        heal_component_count=1,
        can_crit=True,
        legal=True,
        blockers=(),
    )


PURE_WARDEN = ExtremeHealClassRoute(
    base_class=CharacterClass.WARDEN,
    configuration=ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "animal_companions",
            "green_balance",
            "winters_embrace",
        )
    ),
)
SUBCLASS_WARDEN = ExtremeHealClassRoute(
    base_class=CharacterClass.WARDEN,
    configuration=ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "green_balance",
            "restoring_light",
            "storm_calling",
        )
    ),
)
PURE_TEMPLAR = ExtremeHealClassRoute(
    base_class=CharacterClass.TEMPLAR,
    configuration=ClassSkillLineConfiguration(
        equipped_skill_lines=(
            "aedric_spear",
            "dawns_wrath",
            "restoring_light",
        )
    ),
)


class _Routes:
    def routes_for_base_class(self, base_class):
        assert base_class is CharacterClass.WARDEN
        return (PURE_WARDEN, SUBCLASS_WARDEN)

    @staticmethod
    def materialize_build(build, route):
        result = PlayerBuild.from_dict(build.to_dict())
        result.EsoClass = route.base_class.value
        result.ClassSkillLines = list(route.equipped_skill_lines)
        if route.is_subclassed:
            result.ClassMasteryAbilityIds = []
        return result


class _AllBaseRoutes:
    ROUTES = {
        CharacterClass.WARDEN: (PURE_WARDEN,),
        CharacterClass.TEMPLAR: (PURE_TEMPLAR,),
    }

    def routes_for_base_class(self, base_class):
        return self.ROUTES.get(base_class, ())

    @staticmethod
    def materialize_build(build, route):
        result = PlayerBuild.from_dict(build.to_dict())
        result.EsoClass = route.base_class.value
        result.ClassSkillLines = list(route.equipped_skill_lines)
        if route.is_subclassed:
            result.ClassMasteryAbilityIds = []
        return result


class _ProgressionNormalizer:
    def normalize(self, progression, route):
        marker = 9 if route.base_class is CharacterClass.TEMPLAR else 7
        return replace(
            progression,
            owned_skill_lines=tuple(route.equipped_skill_lines),
            passive_ranks={"Route Passive": marker},
        )


class _Candidates:
    def candidates_for_build(self, build, progression, *, class_configuration=None, include_blocked=False):
        _ = include_blocked
        assert progression.passive_rank("Route Passive") == 7
        lines = set(class_configuration.effective_skill_lines(CharacterClass.WARDEN))
        if "restoring_light" in lines:
            return (_candidate("Breath of Life", skill_line="Restoring Light", class_type="Templar"),)
        return (_candidate("Budding Seeds", skill_line="Green Balance", class_type="Warden"),)


class _AllBaseCandidates:
    def candidates_for_build(self, build, progression, *, class_configuration=None, include_blocked=False):
        _ = class_configuration, include_blocked
        if build.EsoClass == CharacterClass.TEMPLAR.value:
            assert progression.passive_rank("Route Passive") == 9
            return (_candidate("Breath of Life", skill_line="Restoring Light", class_type="Templar"),)
        if build.EsoClass == CharacterClass.WARDEN.value:
            assert progression.passive_rank("Route Passive") == 7
            return (_candidate("Budding Seeds", skill_line="Green Balance", class_type="Warden"),)
        return ()


class _Optimizer:
    def __init__(self):
        self.optimizer = SimpleNamespace(
            database_path=Path("fake.db"),
            build_service=SimpleNamespace(
                canonical=SimpleNamespace(catalog_service=object())
            ),
        )
        self.progression_overrides = []

    def optimize(
        self,
        build,
        entity_id,
        *,
        active_bar="front",
        max_passes=24,
        progression_override=None,
    ):
        _ = max_passes
        assert progression_override is not None
        self.progression_overrides.append(progression_override)
        skills = build.BackBarSkills if active_bar == "back" else build.FrontBarSkills
        slot = next(index for index, name in enumerate(skills[:5]) if name.casefold().replace(" ", "_") == entity_id)
        subclass = "restoring_light" in build.ClassSkillLines
        base = 2000.0 if subclass else 1000.0
        score = base + (100.0 if slot == 3 else float(slot))
        event = SimpleNamespace(critical_heal=score)
        return SimpleNamespace(
            optimized_event=event,
            mechanic_complete=True,
            unresolved=(),
        )


class _AllBaseOptimizer(_Optimizer):
    def optimize(
        self,
        build,
        entity_id,
        *,
        active_bar="front",
        max_passes=24,
        progression_override=None,
    ):
        _ = entity_id, max_passes
        assert progression_override is not None
        self.progression_overrides.append(progression_override)
        skills = build.BackBarSkills if active_bar == "back" else build.FrontBarSkills
        slot = next(index for index, name in enumerate(skills[:5]) if name)
        route_passive = float(progression_override.passive_rank("Route Passive") or 0)
        base = 3000.0 if build.EsoClass == CharacterClass.TEMPLAR.value else 1500.0
        event = SimpleNamespace(critical_heal=base + route_passive + float(slot))
        return SimpleNamespace(
            optimized_event=event,
            mechanic_complete=True,
            unresolved=(),
        )


def _install_progression(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        progression=CharacterProgression(),
        unresolved=(),
    )

    class _Adapter:
        def __init__(self, catalog):
            _ = catalog

        def resolve(self, build):
            _ = build
            return resolution

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)


def _service(*, optimizer, candidates, routes):
    return ExtremeActualHealClassRouteCatalogService(
        optimizer=optimizer,
        candidates=candidates,
        routes=routes,
        progression_normalizer=_ProgressionNormalizer(),
    )


def test_route_catalog_scores_subclass_heal_on_materialized_route(monkeypatch):
    _install_progression(monkeypatch)
    baseline = PlayerBuild(
        EsoClass="Warden",
        FrontBarSkills=["Old 1", "Old 2", "Old 3", "Old 4", "Old 5", "Ultimate"],
        ClassMasteryAbilityIds=[111, 222],
    )
    optimizer = _Optimizer()
    service = _service(
        optimizer=optimizer,
        candidates=_Candidates(),
        routes=_Routes(),
    )

    result = service.rank(baseline)

    assert result.best_scored is not None
    assert result.best_scored.candidate.name == "Breath of Life"
    assert result.best_scored.route is SUBCLASS_WARDEN
    assert result.best_scored.slotted_index == 3
    assert result.best_scored.critical_heal == 2100.0
    assert result.best_scored.candidate_build.FrontBarSkills[3] == "Breath of Life"
    assert result.best_scored.candidate_build.FrontBarSkills[5] == "Ultimate"
    assert set(result.best_scored.candidate_build.ClassSkillLines) == {
        "green_balance",
        "restoring_light",
        "storm_calling",
    }
    assert result.best_scored.candidate_build.ClassMasteryAbilityIds == []
    assert optimizer.progression_overrides
    assert all(item.passive_rank("Route Passive") == 7 for item in optimizer.progression_overrides)


def test_route_catalog_searches_all_five_ordinary_slots_and_preserves_ultimate(monkeypatch):
    _install_progression(monkeypatch)
    baseline = PlayerBuild(
        EsoClass="Warden",
        FrontBarSkills=["A", "B", "C", "D", "E", "Ultimate"],
    )
    service = _service(
        optimizer=_Optimizer(),
        candidates=_Candidates(),
        routes=_Routes(),
    )

    result = service.rank(baseline)
    budding = next(entry for entry in result.entries if entry.candidate.name == "Budding Seeds")

    assert budding.slotted_index == 3
    assert budding.candidate_build.FrontBarSkills == ["A", "B", "C", "Budding Seeds", "E", "Ultimate"]


def test_route_catalog_keeps_global_proof_false_while_class_passive_scope_is_incomplete(monkeypatch):
    _install_progression(monkeypatch)
    service = _service(
        optimizer=_Optimizer(),
        candidates=_Candidates(),
        routes=_Routes(),
    )

    result = service.rank(PlayerBuild(EsoClass="Warden"))

    assert result.best_scored is not None
    assert result.best_complete is not None
    assert result.global_maximum_proven is False
    assert "base-class change" in result.omitted_scope
    assert "complete class-line passive/proc coverage for every equipped route" in result.omitted_scope
    assert "hypothetical selected-class-line max progression normalization" in result.search_scope
    assert "selected heal replacement across the five ordinary active-bar slots" in result.search_scope


def test_route_catalog_searches_all_base_classes_with_normalized_progression(monkeypatch):
    _install_progression(monkeypatch)
    baseline = PlayerBuild(
        EsoClass="Warden",
        FrontBarSkills=["", "", "", "", "", "Ultimate"],
    )
    optimizer = _AllBaseOptimizer()
    service = _service(
        optimizer=optimizer,
        candidates=_AllBaseCandidates(),
        routes=_AllBaseRoutes(),
    )

    result = service.rank(baseline, include_base_class_changes=True)

    assert {entry.route.base_class for entry in result.entries} == {
        CharacterClass.WARDEN,
        CharacterClass.TEMPLAR,
    }
    assert result.best_scored is not None
    assert result.best_scored.route.base_class is CharacterClass.TEMPLAR
    assert result.best_scored.candidate.name == "Breath of Life"
    assert result.best_scored.candidate_build.EsoClass == CharacterClass.TEMPLAR.value
    assert "all seven ESO base classes" in result.search_scope
    assert "hypothetical selected-class-line max progression normalization" in result.search_scope
    assert "base-class change" not in result.omitted_scope
    assert "hypothetical alternate-base-class passive/progression normalization" not in result.omitted_scope
    assert any(item.passive_rank("Route Passive") == 9 for item in optimizer.progression_overrides)
    assert result.global_maximum_proven is False
