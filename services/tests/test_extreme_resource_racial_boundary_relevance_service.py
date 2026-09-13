from services.extreme_resource_racial_boundary_relevance_service import (
    ExtremeResourceRacialBoundaryRelevanceService,
)


class _Repository:
    NONCOMBAT_PASSIVE_NAMES = frozenset({"diplomat"})
    MITIGATION_PASSIVE_NAMES = frozenset({"acrobat"})
    RESOURCE_SUSTAIN_PASSIVE_NAMES = frozenset({"spell recharge"})
    CONSUMABLE_DURATION_PASSIVE_NAMES = frozenset({"reveler"})


def _service():
    return ExtremeResourceRacialBoundaryRelevanceService(repository=_Repository())


def test_ability_cost_boundary_is_irrelevant_to_max_resource_snapshot():
    report = _service().build(
        "max_health",
        ("Racial ability-cost reduction requires cost-stat model: Red Diamond",),
    )

    assert report.denominator_proven
    assert report.objective_irrelevance_proven
    assert report.unresolved == ()
    assert report.proven_irrelevant == (
        "Racial ability-cost reduction requires cost-stat model: Red Diamond",
    )


def test_environmental_mitigation_boundary_is_irrelevant_to_max_resource_snapshot():
    message = "Racial environmental-damage mitigation requires mitigation model: Acrobat"
    report = _service().build("max_stamina", (message,))

    assert report.denominator_proven
    assert report.objective_irrelevance_proven
    assert report.unresolved == ()
    assert report.proven_irrelevant == (message,)


def test_unknown_racial_boundary_stays_fail_closed():
    report = _service().build("max_health", ("Unknown racial warning: Mystery",))

    assert report.denominator_proven
    assert not report.objective_irrelevance_proven
    assert report.proven_irrelevant == ()
    assert report.unresolved == ("Unknown racial warning: Mystery",)
