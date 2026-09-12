from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_resource_attribute_projection_service import (
    ExtremeResourceAttributeProjectionService,
)


def _full_allocations():
    return ExtremeGlobalSearchUniverseService.attribute_allocations()


def test_max_resource_objectives_reduce_full_simplex_to_all_in_target_witness():
    expected = {
        "max_health": AttributeAllocation(health=64, magicka=0, stamina=0),
        "max_magicka": AttributeAllocation(health=0, magicka=64, stamina=0),
        "max_stamina": AttributeAllocation(health=0, magicka=0, stamina=64),
    }

    for objective, witness in expected.items():
        projection = ExtremeResourceAttributeProjectionService.build(
            objective,
            _full_allocations(),
        )
        assert projection.source_allocations_reviewed == 2145
        assert projection.denominator_proven is True
        assert projection.projection_complete is True
        assert projection.allocations == (witness,)
        assert projection.per_point_value > 0.0
        assert projection.unresolved == ()


def test_incomplete_source_simplex_fails_closed_and_returns_no_projection():
    projection = ExtremeResourceAttributeProjectionService.build(
        "max_health",
        (
            AttributeAllocation(health=64, magicka=0, stamina=0),
            AttributeAllocation(health=0, magicka=64, stamina=0),
        ),
    )

    assert projection.denominator_proven is False
    assert projection.projection_complete is False
    assert projection.allocations == ()
    assert projection.unresolved


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeResourceAttributeProjectionService.build(
            "spell_damage",
            _full_allocations(),
        )
    except KeyError as exc:
        assert "unreviewed Extreme resource attribute objective" in str(exc)
    else:
        raise AssertionError("expected unreviewed objective to fail closed")
