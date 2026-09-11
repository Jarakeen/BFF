from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveReviewService,
    ExtremeResourceContextualPassiveStatus,
)


def _by_name(objective: str):
    return {
        row.passive_name: row
        for row in ExtremeResourceContextualPassiveReviewService.build(objective)
    }


def test_max_health_review_marks_bar_and_runtime_passives_applied():
    rows = _by_name("max_health")

    assert rows["Last Gasp"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Juggernaut"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Dark Vigor"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Nothing Wasted"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Last Gasp"].source == "NecromancerPassiveInputResolver"
    assert rows["Juggernaut"].source == "ArmorPassiveInputResolver"
    assert rows["Dark Vigor"].source == "NightbladePassiveInputResolver"
    assert rows["Expert Summoner"].source == "ExtremeSorcererExpertSummonerPetContextService"
    assert rows["Nothing Wasted"].source == "ClassMasteryExtremeEffectService"
    assert "six-slot" in rows["Dark Vigor"].condition.casefold()
    assert "permanent-pet" in rows["Expert Summoner"].condition.casefold()
    assert "10-stack" in rows["Nothing Wasted"].condition.casefold()
    assert "pure necromancer" in rows["Nothing Wasted"].condition.casefold()
    assert "heavy armor" in rows["Juggernaut"].condition.casefold()
    assert "max-health" in rows["Juggernaut"].condition.casefold()


def test_max_magicka_review_marks_joint_bar_passives_applied():
    rows = _by_name("max_magicka")

    assert set(rows) == {"Expert Summoner", "Magicka Flood", "Magicka Controller"}
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Magicka Flood"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Magicka Controller"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Magicka Flood"].source == "NightbladePassiveInputResolver"
    assert rows["Magicka Controller"].source == "GuildPassiveInputResolver"
    assert "jointly" in rows["Magicka Flood"].condition.casefold()
    assert "jointly" in rows["Magicka Controller"].condition.casefold()


def test_max_stamina_review_marks_siphoning_bar_trigger_applied():
    rows = _by_name("max_stamina")

    assert set(rows) == {"Expert Summoner", "Magicka Flood"}
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Magicka Flood"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert "one legal siphoning" in rows["Magicka Flood"].condition.casefold()


def test_status_filter_is_deterministic_and_reviewed_runtime_bucket_is_empty():
    first = ExtremeResourceContextualPassiveReviewService.status_rows(
        "max_health",
        ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
    )
    second = ExtremeResourceContextualPassiveReviewService.status_rows(
        "MAX_HEALTH",
        ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
    )

    assert first == second == ()
    assert not hasattr(first, "denominator_proven")


def test_no_reviewed_high_impact_resource_passive_still_needs_engineering_boundary():
    rows = (
        *ExtremeResourceContextualPassiveReviewService.build("max_health"),
        *ExtremeResourceContextualPassiveReviewService.build("max_magicka"),
        *ExtremeResourceContextualPassiveReviewService.build("max_stamina"),
    )

    assert rows
    assert all(
        row.status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
        for row in rows
    )


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeResourceContextualPassiveReviewService.build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme contextual resource objective" in str(exc)
    else:
        raise AssertionError("expected unsupported contextual resource objective to fail closed")
