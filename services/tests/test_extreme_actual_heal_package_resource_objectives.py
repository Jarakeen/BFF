from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)


RESOURCE_OBJECTIVES = {"max_health", "max_magicka", "max_stamina"}


def test_monster_package_discovery_includes_resource_scaling_objectives():
    assert RESOURCE_OBJECTIVES.issubset(
        set(ExtremeActualHealMonsterPackageService.OBJECTIVES)
    )


def test_double_five_package_discovery_includes_resource_scaling_objectives():
    assert RESOURCE_OBJECTIVES.issubset(
        set(ExtremeActualHealDoubleFivePackageService.OBJECTIVES)
    )


def test_mythic_package_discovery_includes_resource_scaling_objectives():
    assert RESOURCE_OBJECTIVES.issubset(
        set(ExtremeActualHealMythicPackageService.OBJECTIVES)
    )
