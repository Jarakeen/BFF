from models.performance_model import PerformanceProfile
from services.performance_raid_review_lokkestiiz_profile_request_service import (
    PerformanceRaidReviewLokkestiizProfileRequestService,
)


def _profile(report: str, fight: str, actor_id: int, label: str, role: str) -> PerformanceProfile:
    return PerformanceProfile(
        ReportCode=report,
        FightId=fight,
        ActorId=actor_id,
        ActorLabel=label,
        Role=role,
    )


def test_builds_one_lokke_pull_request_from_same_pull_profiles() -> None:
    profiles = (
        _profile("ABC", "7", 11, "Magrat", "Healer"),
        _profile("ABC", "7", 12, "Main Tank", "Tank"),
        _profile("ABC", "7", 13, "DD One", "DPS"),
    )

    result = PerformanceRaidReviewLokkestiizProfileRequestService().build(
        profiles,
        boss_actor_id=99,
        member_keys={
            ("ABC", 11): "magrat",
            ("ABC", 12): "main-tank",
            ("ABC", 13): "dd-one",
        },
    )

    assert result.request is not None
    assert result.request.report_code == "ABC"
    assert result.request.fight_id == 7
    assert result.request.boss_actor_id == 99
    assert [source.member_key for source in result.request.sources] == [
        "magrat",
        "main-tank",
        "dd-one",
    ]
    assert not result.unresolved


def test_profiles_from_multiple_pulls_are_rejected_instead_of_merged() -> None:
    profiles = (
        _profile("ABC", "7", 11, "Magrat", "Healer"),
        _profile("ABC", "8", 12, "Main Tank", "Tank"),
    )

    result = PerformanceRaidReviewLokkestiizProfileRequestService().build(
        profiles,
        boss_actor_id=99,
    )

    assert result.request is None
    assert len(result.unresolved) == 1
    assert "multiple pulls" in result.unresolved[0]
    assert "ABC #7" in result.unresolved[0]
    assert "ABC #8" in result.unresolved[0]


def test_invalid_boss_actor_id_fails_closed() -> None:
    result = PerformanceRaidReviewLokkestiizProfileRequestService().build(
        (_profile("ABC", "7", 11, "Magrat", "Healer"),),
        boss_actor_id=0,
    )

    assert result.request is None
    assert any("positive boss_actor_id" in message for message in result.unresolved)


def test_invalid_profiles_remain_unresolved_while_valid_same_pull_rows_build() -> None:
    profiles = (
        PerformanceProfile(),
        _profile("ABC", "7", 11, "Magrat", "Healer"),
    )

    result = PerformanceRaidReviewLokkestiizProfileRequestService().build(
        profiles,
        boss_actor_id=99,
    )

    assert result.request is not None
    assert len(result.request.sources) == 1
    assert any("Performance profile 1" in message for message in result.unresolved)


def test_no_valid_profiles_cannot_create_pull_request() -> None:
    result = PerformanceRaidReviewLokkestiizProfileRequestService().build(
        (PerformanceProfile(),),
        boss_actor_id=99,
    )

    assert result.request is None
    assert any("No valid Performance profiles" in message for message in result.unresolved)
