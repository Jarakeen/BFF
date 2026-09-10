from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from services.performance_raid_review_healer_effect_coverage_service import (
    PerformanceRaidReviewHealerEffectCoverageService,
    RaidReviewHealerEffectRequirement,
)
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow


def _mechanic(key="ice_cage_one", start=10.0):
    return RaidReviewEncounterWindow(
        report_code="A",
        fight_id=1,
        semantic_key=key,
        label="Ice Cage One",
        start_seconds=start,
        end_seconds=start + 8.0,
        evidence_source="reviewed encounter evidence",
        reviewed=True,
    )


def test_effect_active_at_mechanic_start_satisfies_requirement() -> None:
    result = PerformanceRaidReviewHealerEffectCoverageService().evaluate(
        effect_windows=[
            RuntimeEffectActiveWindow(
                "Budding Seeds",
                "esologs:actor:11",
                8.0,
                14.0,
                target="esologs:actor:21",
            )
        ],
        mechanic_windows=[_mechanic()],
        requirements=[
            RaidReviewHealerEffectRequirement(
                "budding_seeds_precoverage",
                "Budding Seeds Pre-Coverage",
                ("Budding Seeds",),
                ("ice_cage_one",),
                source_actor_id=11,
            )
        ],
    )

    assert result.unresolved == ()
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.covered
    assert observation.active_target_count == 1
    assert observation.active_effect_names == ("Budding Seeds",)


def test_effect_starting_after_mechanic_does_not_count_as_precoverage() -> None:
    result = PerformanceRaidReviewHealerEffectCoverageService().evaluate(
        effect_windows=[
            RuntimeEffectActiveWindow(
                "Illustrious Healing",
                "esologs:actor:11",
                10.1,
                20.0,
                target="esologs:actor:21",
            )
        ],
        mechanic_windows=[_mechanic()],
        requirements=[
            RaidReviewHealerEffectRequirement(
                "illustrious_precoverage",
                "Illustrious Healing Pre-Coverage",
                ("Illustrious Healing",),
                ("ice_cage_one",),
                source_actor_id=11,
            )
        ],
    )

    assert not result.observations[0].covered
    assert result.observations[0].active_target_count == 0


def test_source_actor_filter_prevents_crediting_other_healer() -> None:
    result = PerformanceRaidReviewHealerEffectCoverageService().evaluate(
        effect_windows=[
            RuntimeEffectActiveWindow(
                "Budding Seeds",
                "esologs:actor:12",
                8.0,
                14.0,
                target="esologs:actor:21",
            )
        ],
        mechanic_windows=[_mechanic()],
        requirements=[
            RaidReviewHealerEffectRequirement(
                "budding_seeds_precoverage",
                "Budding Seeds Pre-Coverage",
                ("Budding Seeds",),
                ("ice_cage_one",),
                source_actor_id=11,
            )
        ],
    )

    assert not result.observations[0].covered


def test_minimum_target_requirement_uses_distinct_active_targets() -> None:
    result = PerformanceRaidReviewHealerEffectCoverageService().evaluate(
        effect_windows=[
            RuntimeEffectActiveWindow("Combat Prayer", "esologs:actor:11", 9.0, 15.0, target="esologs:actor:21"),
            RuntimeEffectActiveWindow("Combat Prayer", "esologs:actor:11", 9.1, 15.0, target="esologs:actor:22"),
        ],
        mechanic_windows=[_mechanic()],
        requirements=[
            RaidReviewHealerEffectRequirement(
                "combat_prayer_precoverage",
                "Combat Prayer Pre-Coverage",
                ("Combat Prayer",),
                ("ice_cage_one",),
                source_actor_id=11,
                minimum_active_targets=2,
            )
        ],
    )

    assert result.observations[0].covered
    assert result.observations[0].active_target_count == 2


def test_missing_reviewed_mechanic_is_explicitly_unresolved() -> None:
    result = PerformanceRaidReviewHealerEffectCoverageService().evaluate(
        effect_windows=(),
        mechanic_windows=(),
        requirements=[
            RaidReviewHealerEffectRequirement(
                "budding_seeds_precoverage",
                "Budding Seeds Pre-Coverage",
                ("Budding Seeds",),
                ("ice_cage_one",),
            )
        ],
    )

    assert result.observations == ()
    assert result.unresolved == (
        "Budding Seeds Pre-Coverage: reviewed mechanic window ice_cage_one was not available for coverage evaluation.",
    )


def test_unreviewed_requirement_is_not_interpreted() -> None:
    result = PerformanceRaidReviewHealerEffectCoverageService().evaluate(
        effect_windows=(),
        mechanic_windows=[_mechanic()],
        requirements=[
            RaidReviewHealerEffectRequirement(
                "experimental",
                "Experimental",
                ("Mystery Effect",),
                ("ice_cage_one",),
                reviewed=False,
            )
        ],
    )

    assert result.observations == ()
    assert result.unresolved == ()
