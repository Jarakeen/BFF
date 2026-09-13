from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.champion_point_loadout_service import ChampionPointLoadoutCandidate
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)
from services.extreme_health_recovery_runtime_compatibility_service import (
    ExtremeHealthRecoveryCompatibility,
    ExtremeHealthRecoveryRuntimeCompatibilityService,
    ExtremeHealthRecoveryRuntimeState,
)


def _branch(name: str, description: str, pieces: int = 5):
    row = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name=name,
        piece_count=pieces,
        description=description,
        objective_key="health_recovery",
    )
    assert row is not None
    return row


def test_dominant_shared_runtime_state_is_jointly_compatible():
    state = ExtremeHealthRecoveryRuntimeState()
    assert state.dominant_shared_state_compatible is True


def test_green_pact_requires_food_instead_of_direct_drink_incumbent():
    branch = _branch(
        "Green Pact",
        "While you have a food buff active, your Health Recovery is increased by 8-356 and your Max Health by 2500.",
    )
    result = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
        branch, ExtremeHealthRecoveryRuntimeState(provisioning_kind="drink")
    )
    assert result.status is ExtremeHealthRecoveryCompatibility.ALTERNATE_PROVISIONING


def test_major_fortitude_set_is_redundant_when_potion_buff_is_active():
    branch = _branch(
        "Apocryphal Inspiration",
        "You and group members gain Major Fortitude, Major Intellect, and Major Endurance, increasing recovery by 30%.",
    )
    result = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
        branch, ExtremeHealthRecoveryRuntimeState(major_fortitude_active=True)
    )
    assert result.status is ExtremeHealthRecoveryCompatibility.REDUNDANT_NAMED_BUFF


def test_low_health_and_recent_ultimate_branches_can_coexist_with_dominant_state():
    state = ExtremeHealthRecoveryRuntimeState()
    orgnum = _branch(
        "Orgnum's Scales",
        "While you are below 60% Health, increase your Health Recovery by 800 and your Physical and Spell Resistance by 6400.",
    )
    soulwell = _branch(
        "Lustrous Soulwell",
        "After using an Ultimate, gain 465 Health, Magicka, and Stamina Recovery.",
    )
    assert ExtremeHealthRecoveryRuntimeCompatibilityService.assess(orgnum, state).status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
    assert ExtremeHealthRecoveryRuntimeCompatibilityService.assess(soulwell, state).status is ExtremeHealthRecoveryCompatibility.COMPATIBLE


def test_twice_born_star_remains_separate_search_state():
    branch = _branch(
        "Twice-Born Star",
        "You can have two Mundus Stone boons at the same time.",
    )
    result = ExtremeHealthRecoveryRuntimeCompatibilityService.assess(
        branch, ExtremeHealthRecoveryRuntimeState()
    )
    assert result.status is ExtremeHealthRecoveryCompatibility.SEARCH_STATE_MUTATION

def _cp(name: str, ceiling: float, condition: str | None = None):
    return ChampionPointLoadoutCandidate(
        name=name,
        discipline_index=3,
        flat_ceiling=ceiling,
        condition=condition,
    )


def test_rejuvenation_peace_and_suffering_can_share_one_runtime_state():
    state = ExtremeHealthRecoveryRuntimeState(
        crowd_control_immunity_active=True,
        negative_effect_active=True,
    )
    rows = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_points(
        (
            _cp("Rejuvenation", 90.0),
            _cp("Peace of Mind", 200.0),
            _cp("Sustained by Suffering", 150.0),
        ),
        state,
    )

    assert all(row.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE for row in rows)


def test_enlivening_overflow_requires_exact_max_magicka_before_claiming_cap():
    candidate = _cp("Enlivening Overflow", 150.0)
    unresolved = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_point(
        candidate,
        ExtremeHealthRecoveryRuntimeState(max_magicka=None),
    )
    compatible = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_point(
        candidate,
        ExtremeHealthRecoveryRuntimeState(max_magicka=30000.0),
    )

    assert unresolved.status is ExtremeHealthRecoveryCompatibility.RUNTIME_PROOF_REQUIRED
    assert unresolved.required_max_magicka == 30000.0
    assert compatible.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE


def test_enlivening_overflow_buff_can_precede_low_health_scoring_state():
    row = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_point(
        _cp("Enlivening Overflow", 150.0),
        ExtremeHealthRecoveryRuntimeState(
            max_magicka=30000.0,
            enlivening_overflow_trigger_seconds=20.0,
            low_health_boundary_seconds=21.0,
            score_seconds=24.999,
        ),
    )

    assert row.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE


def test_strategic_reserve_reports_ultimate_gap_inside_booming_voice_window():
    events = (UltimateGenerationEvent(24.0, 136.0, "reviewed modeled generation"),)
    row = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_point(
        _cp("Strategic Reserve", 1500.0),
        ExtremeHealthRecoveryRuntimeState(ultimate_generation_events=events),
    )

    assert row.status is ExtremeHealthRecoveryCompatibility.RUNTIME_PROOF_REQUIRED
    assert row.available_ultimate_at_score == 386.0
    assert row.ultimate_shortfall == 114.0


def test_strategic_reserve_is_compatible_when_explicit_generation_refills_cap():
    events = (UltimateGenerationEvent(24.0, 250.0, "complete reviewed generation"),)
    row = ExtremeHealthRecoveryRuntimeCompatibilityService.assess_champion_point(
        _cp("Strategic Reserve", 1500.0),
        ExtremeHealthRecoveryRuntimeState(ultimate_generation_events=events),
    )

    assert row.status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
    assert row.available_ultimate_at_score == 500.0
    assert row.ultimate_shortfall == 0.0
