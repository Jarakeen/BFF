from __future__ import annotations

import inspect

from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)

from services.extreme_actual_heal_package_admission_denominator_service import (
    ExtremeActualHealPackageAdmissionFamily,
)


def test_package_admission_family_reports_missing_and_unexpected_case_insensitively() -> None:
    row = ExtremeActualHealPackageAdmissionFamily(
        family="mythic",
        expected=("Oakensoul Ring", "Markyn Ring of Majesty"),
        admitted=("oakensoul ring", "Something Else"),
    )

    assert row.missing == ("Markyn Ring of Majesty",)
    assert row.unexpected == ("Something Else",)
    assert row.proven is False


def test_package_admission_family_is_proven_for_exact_exhaustive_match() -> None:
    row = ExtremeActualHealPackageAdmissionFamily(
        family="monster",
        expected=("A", "B"),
        admitted=("A", "B"),
    )

    assert row.missing == ()
    assert row.unexpected == ()
    assert row.proven is True


def test_package_builders_are_exhaustive_by_default() -> None:
    monster = inspect.signature(
        ExtremeActualHealMonsterPackageService.build_candidates
    ).parameters
    assert monster["ordinary_per_objective"].default is None
    assert monster["monster_per_objective"].default is None

    double_five = inspect.signature(
        ExtremeActualHealDoubleFivePackageService.build_candidates
    ).parameters
    assert double_five["primary_per_objective"].default is None
    assert double_five["secondary_per_objective"].default is None

    ring = inspect.signature(
        ExtremeActualHealMythicPackageService.build_candidates
    ).parameters
    assert ring["primary_per_objective"].default is None
    assert ring["secondary_per_objective"].default is None
    assert ring["mythic_per_objective"].default is None

    non_ring = inspect.signature(
        ExtremeActualHealNonRingMythicPackageService.build_candidates
    ).parameters
    assert non_ring["ordinary_per_objective"].default is None
    assert non_ring["mythic_per_objective"].default is None
