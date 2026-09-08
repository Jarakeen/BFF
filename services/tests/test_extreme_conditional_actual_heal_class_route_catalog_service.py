import pytest

from models.build_model import PlayerBuild
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogResult,
)
from services.extreme_conditional_actual_heal_class_route_catalog_service import (
    ExtremeConditionalActualHealClassRouteCatalogService,
)


class _Catalog:
    def __init__(self):
        self.calls = []

    def rank(
        self,
        baseline_build,
        *,
        active_bar="front",
        max_passes=24,
        include_base_class_changes=False,
    ):
        self.calls.append(
            (
                baseline_build.BuildName,
                active_bar,
                max_passes,
                include_base_class_changes,
            )
        )
        return ExtremeActualHealClassRouteCatalogResult(
            entries=(),
            best_scored=None,
            best_complete=None,
            search_scope=("existing route search",),
            omitted_scope=("remaining mechanic gap",),
        )


def test_conditional_route_catalog_defaults_to_cross_class_search_and_labels_scenario():
    catalog = _Catalog()
    service = ExtremeConditionalActualHealClassRouteCatalogService(
        target_health_fraction=0.29,
        catalog=catalog,
    )

    result = service.rank(
        PlayerBuild(BuildName="Emergency Healer"),
        active_bar="back",
        max_passes=12,
    )

    assert catalog.calls == [("Emergency Healer", "back", 12, True)]
    assert result.search_scope[0] == "explicit conditional target health fraction 0.290000"
    assert result.search_scope[1:] == ("existing route search",)
    assert result.omitted_scope == ("remaining mechanic gap",)


def test_conditional_route_catalog_can_deliberately_hold_base_class_fixed():
    catalog = _Catalog()
    service = ExtremeConditionalActualHealClassRouteCatalogService(
        target_health_fraction=0.30,
        catalog=catalog,
    )

    service.rank(
        PlayerBuild(BuildName="Fixed Class"),
        include_base_class_changes=False,
    )

    assert catalog.calls[-1][3] is False


def test_conditional_route_catalog_rejects_invalid_target_health_fraction():
    with pytest.raises(ValueError, match="target_health_fraction"):
        ExtremeConditionalActualHealClassRouteCatalogService(
            target_health_fraction=1.01,
            catalog=_Catalog(),
        )
