from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveReviewService,
    ExtremeResourceContextualPassiveStatus,
)


def _by_name(objective: str):
    return {
        row.passive_name: row
        for row in ExtremeResourceContextualPassiveReviewService.build(objective)
    }


def test_max_health_review_separates_applied_bar_runtime_and_missing_mechanics():
    rows = _by_name("max_health")

    assert rows["Last Gasp"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Dark Vigor"].status is ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED
    assert rows["Nothing Wasted"].status is ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED
    assert rows["Juggernaut"].status is ExtremeResourceContextualPassiveStatus.MECHANIC_IMPLEMENTATION_REQUIRED
    assert rows["Last Gasp"].source == "NecromancerPassiveInputResolver"
    assert "permanent pet" in rows["Expert Summoner"].condition.casefold()
    assert "10-stack" in rows["Nothing Wasted"].condition.casefold()
    assert "heavy armor" in rows["Juggernaut"].condition.casefold()


def test_max_magicka_review_keeps_standing_summoner_separate_from_bar_search():
    rows = _by_name("max_magicka")

    assert set(rows) == {"Expert Summoner", "Magicka Flood", "Magicka Controller"}
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Magicka Flood"].status is ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED
    assert rows["Magicka Controller"].status is ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED
    assert rows["Magicka Flood"].source == "NightbladePassiveInputResolver"
    assert rows["Magicka Controller"].source == "GuildPassiveInputResolver"


def test_max_stamina_review_tracks_existing_summoner_math_and_siphoning_bar_gap():
    rows = _by_name("max_stamina")

    assert set(rows) == {"Expert Summoner", "Magicka Flood"}
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Magicka Flood"].status is ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED


def test_status_filter_is_deterministic_and_does_not_claim_global_denominator():
    first = ExtremeResourceContextualPassiveReviewService.status_rows(
        "max_health",
        ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
    )
    second = ExtremeResourceContextualPassiveReviewService.status_rows(
        "MAX_HEALTH",
        ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
    )

    assert first == second
    assert [row.passive_name for row in first] == ["Expert Summoner", "Nothing Wasted"]
    assert not hasattr(first, "denominator_proven")


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeResourceContextualPassiveReviewService.build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme contextual resource objective" in str(exc)
    else:
        raise AssertionError("expected unsupported contextual resource objective to fail closed")
