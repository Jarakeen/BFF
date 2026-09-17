from services.extreme_unresolved_incumbent_admission_service import (
    ExtremeUnresolvedIncumbentAdmissionService,
)


def test_clean_incumbent_rejects_candidate_with_new_blocker() -> None:
    result = ExtremeUnresolvedIncumbentAdmissionService.review(
        (),
        ("new blocker",),
    )
    assert result.admissible is False
    assert result.introduced == ("new blocker",)
    assert result.inherited == ()
    assert result.removed == ()


def test_candidate_may_preserve_same_inherited_blocker() -> None:
    result = ExtremeUnresolvedIncumbentAdmissionService.review(
        ("existing blocker",),
        ("existing blocker",),
    )
    assert result.admissible is True
    assert result.introduced == ()
    assert result.inherited == ("existing blocker",)
    assert result.removed == ()


def test_candidate_may_remove_inherited_blocker() -> None:
    result = ExtremeUnresolvedIncumbentAdmissionService.review(
        ("existing blocker",),
        (),
    )
    assert result.admissible is True
    assert result.introduced == ()
    assert result.inherited == ()
    assert result.removed == ("existing blocker",)


def test_candidate_cannot_swap_inherited_blocker_for_new_blocker() -> None:
    result = ExtremeUnresolvedIncumbentAdmissionService.review(
        ("old blocker",),
        ("new blocker",),
    )
    assert result.admissible is False
    assert result.introduced == ("new blocker",)
    assert result.inherited == ()
    assert result.removed == ("old blocker",)


def test_duplicate_blocker_text_does_not_create_false_new_identity() -> None:
    result = ExtremeUnresolvedIncumbentAdmissionService.review(
        ("same", "same"),
        ("same", "same"),
    )
    assert result.admissible is True
    assert result.inherited == ("same",)
