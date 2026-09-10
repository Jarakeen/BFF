from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverse
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_structural_global_search_service import (
    ExtremeStructuralGlobalSearchService,
)


@dataclass
class _UniverseService:
    universe: ExtremeGlobalSearchUniverse

    def build(self):
        return self.universe


def _route(base_class=CharacterClass.WARDEN, lines=("animal_companions", "green_balance", "winters_embrace")):
    return ExtremeHealClassRoute(
        base_class=base_class,
        configuration=ClassSkillLineConfiguration(equipped_skill_lines=lines),
    )


def _universe(*, deferred=("gear",)):
    return ExtremeGlobalSearchUniverse(
        races=("Argonian", "Breton"),
        class_routes=(
            _route(),
            _route(CharacterClass.SORCERER, ("daedric_summoning", "dark_magic", "storm_calling")),
        ),
        attribute_allocations=(
            AttributeAllocation(health=64, magicka=0, stamina=0),
            AttributeAllocation(health=0, magicka=64, stamina=0),
        ),
        active_bars=("front", "back"),
        structural_scope=("races", "routes", "attributes", "bars"),
        deferred_dynamic_axes=tuple(deferred),
    )


def test_candidate_count_matches_cartesian_structural_denominator():
    universe = _universe()
    assert ExtremeStructuralGlobalSearchService.candidate_count(universe) == 16


def test_search_scores_every_structural_candidate_and_picks_maximum():
    universe = _universe()

    def scorer(objective_key, candidate):
        assert objective_key == "max_health"
        value = float(candidate.attributes.health)
        if candidate.race == "Argonian":
            value += 10.0
        if candidate.active_bar == "back":
            value += 1.0
        return value, {"id": candidate.identity}, ()

    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(universe),
        scorer=scorer,
    ).search("MAX_HEALTH")

    assert result.candidates_scored == 16
    assert result.structural_denominator_proven is True
    assert result.global_denominator_proven is False
    assert result.best is not None
    assert result.best.value == 75.0
    assert result.best.candidate.race == "Argonian"
    assert result.best.candidate.attributes.health == 64
    assert result.best.candidate.active_bar == "back"


def test_ties_are_counted_and_deterministically_resolved_by_identity():
    universe = _universe()

    def scorer(_objective_key, _candidate):
        return 100.0, None, ()

    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(universe),
        scorer=scorer,
    ).search("spell_damage")

    assert result.ties_at_best == 16
    assert result.best is not None
    assert result.best.candidate.identity == min(
        (
            race,
            route.base_class.value,
            tuple(route.equipped_skill_lines),
            allocation.health,
            allocation.magicka,
            allocation.stamina,
            bar,
        )
        for race in universe.races
        for route in universe.class_routes
        for allocation in universe.attribute_allocations
        for bar in universe.active_bars
    )


def test_unresolved_messages_are_deduplicated_without_hiding_score():
    universe = _universe()

    def scorer(_objective_key, candidate):
        message = "dynamic passive unresolved" if candidate.race == "Argonian" else ""
        return 1.0, None, (message,) if message else ()

    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(universe),
        scorer=scorer,
    ).search("weapon_damage")

    assert result.unresolved == ("dynamic passive unresolved",)
    assert result.candidates_scored == 16


def test_no_deferred_axes_allows_global_denominator_only_when_structural_search_is_complete():
    universe = _universe(deferred=())

    result = ExtremeStructuralGlobalSearchService(
        _UniverseService(universe),
        scorer=lambda _key, _candidate: (1.0, None, ()),
    ).search("max_stamina")

    assert result.structural_denominator_proven is True
    assert result.global_denominator_proven is True


def test_blank_objective_is_rejected_before_scoring():
    universe = _universe()
    calls = []

    def scorer(*args):
        calls.append(args)
        return 0.0, None, ()

    service = ExtremeStructuralGlobalSearchService(_UniverseService(universe), scorer=scorer)

    try:
        service.search("   ")
    except ValueError as exc:
        assert "objective_key is required" in str(exc)
    else:
        raise AssertionError("blank objective should fail closed")
    assert calls == []
