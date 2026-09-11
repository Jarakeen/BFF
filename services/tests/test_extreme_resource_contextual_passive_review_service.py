from services.extreme_resource_contextual_passive_review_service import (
    ExtremeResourceContextualPassiveReviewService,
    ExtremeResourceContextualPassiveStatus,
)


def _by_name(objective: str):
    return {
        row.passive_name: row
        for row in ExtremeResourceContextualPassiveReviewService.build(objective)
    }


def test_max_health_review_separates_applied_and_runtime_boundaries():
    rows = _by_name("max_health")

    assert rows["Last Gasp"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Juggernaut"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Dark Vigor"].status is ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED
    assert rows["Expert Summoner"].status is ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED
    assert rows["Nothing Wasted"].status is ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED
    assert rows["Last Gasp"].source == "NecromancerPassiveInputResolver"
    assert rows["Juggernaut"].source == "ArmorPassiveInputResolver"
    assert rows["Dark Vigor"].source == "NightbladePassiveInputResolver"
    assert "six-slot" in rows["Dark Vigor"].condition.casefold()
    assert "permanent pet" in rows["Expert Summoner"].condition.casefold()
    assert "10-stack" in rows["Nothing Wasted"].condition.casefold()
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


def test_no_reviewed_high_impact_resource_passive_still_needs_bar_or_mechanic_implementation():
    rows = (
        *ExtremeResourceContextualPassiveReviewService.build("max_health"),
        *ExtremeResourceContextualPassiveReviewService.build("max_magicka"),
        *ExtremeResourceContextualPassiveReviewService.build("max_stamina"),
    )

    assert not any(
        row.status in {
            ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED,
            ExtremeResourceContextualPassiveStatus.MECHANIC_IMPLEMENTATION_REQUIRED,
        }
        for row in rows
    )


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeResourceContextualPassiveReviewService.build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme contextual resource objective" in str(exc)
    else:
        raise AssertionError("expected unsupported contextual resource objective to fail closed")
