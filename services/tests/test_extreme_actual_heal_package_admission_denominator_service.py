from __future__ import annotations

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
