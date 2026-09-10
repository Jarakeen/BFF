from models.performance_model import PerformanceProfile
from services.performance_raid_review_profile_source_service import (
    PerformanceRaidReviewProfileSourceService,
)


def _profile(
    *,
    report: str = "ABC",
    fight: str = "7",
    actor_id: int | None = 11,
    label: str = "Magrat",
    role: str = "Healer",
    name: str = "My Healer",
) -> PerformanceProfile:
    return PerformanceProfile(
        Name=name,
        ReportCode=report,
        FightId=fight,
        ActorId=actor_id,
        ActorLabel=label,
        Role=role,
        ImmunityBuffName="Invulnerable",
        ImmunityBuffKind="Buff",
    )


def test_valid_profile_becomes_explicit_raid_review_source() -> None:
    result = PerformanceRaidReviewProfileSourceService().build((_profile(),))

    assert not result.unresolved
    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.report_code == "ABC"
    assert source.fight_id == 7
    assert source.actor_id == 11
    assert source.actor_label == "Magrat"
    assert source.role == "Healer"
    assert source.immunity_buff_name == "Invulnerable"
    assert source.immunity_buff_kind == "Buff"
    assert source.member_key == ""
    assert source.primary_resource_name == ""


def test_display_name_is_fallback_label_but_not_inferred_member_key() -> None:
    result = PerformanceRaidReviewProfileSourceService().build(
        (_profile(label="", name="Saved Tank", role="Tank"),)
    )

    assert len(result.sources) == 1
    assert result.sources[0].actor_label == "Saved Tank"
    assert result.sources[0].member_key == ""


def test_explicit_report_scoped_identity_and_resource_mapping_are_preserved() -> None:
    result = PerformanceRaidReviewProfileSourceService().build(
        (_profile(report="ABC", actor_id=11),),
        member_keys={("ABC", 11): "magrat"},
        primary_resources={("ABC", 11): "Magicka"},
    )

    source = result.sources[0]
    assert source.member_key == "magrat"
    assert source.primary_resource_name == "Magicka"


def test_invalid_profiles_are_skipped_without_blocking_valid_profiles() -> None:
    invalid = _profile(report="", fight="nope", actor_id=None, label="", name="")
    valid = _profile(report="XYZ", fight="3", actor_id=22, label="DD One", role="DPS")

    result = PerformanceRaidReviewProfileSourceService().build((invalid, valid))

    assert len(result.sources) == 1
    assert result.sources[0].report_code == "XYZ"
    assert result.sources[0].actor_id == 22
    assert len(result.unresolved) == 1
    assert "Performance profile 1" in result.unresolved[0]
    assert "report code" in result.unresolved[0]
    assert "positive fight id" in result.unresolved[0]
    assert "positive actor id" in result.unresolved[0]
    assert "actor label" in result.unresolved[0]


def test_duplicate_same_report_fight_actor_is_skipped_explicitly() -> None:
    first = _profile(report="ABC", fight="7", actor_id=11, label="Magrat")
    duplicate = _profile(report="abc", fight="7", actor_id=11, label="Magrat Again")

    result = PerformanceRaidReviewProfileSourceService().build((first, duplicate))

    assert len(result.sources) == 1
    assert result.sources[0].actor_label == "Magrat"
    assert result.unresolved == (
        "Duplicate Raid Review source skipped for abc #7 actor 11.",
    )
