from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_team_candidate_optimizer import CompTeamCandidatePool
from services.comp_plan_autofill_service import CompPlanAutoFillService


def _candidate(
    candidate_id: str,
    *,
    name: str,
    source_kind: str = "saved_build",
    source_name: str = "Player",
    eso_class: str = "Warden",
    role: str = "Healer",
    gear_sets: tuple[str, ...] = ("Set A", "Set B"),
    mundus: str = "The Ritual",
    score: float = 100.0,
) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id=candidate_id,
        name=name,
        source_kind=source_kind,
        source_name=source_name,
        source_url="",
        eso_class=eso_class,
        role=role,
        gear_sets=gear_sets,
        skills=(),
        mundus=mundus,
        complete_build=True,
        unresolved=(),
        score=score,
        score_reasons=(),
        five_piece_sets=gear_sets,
    )


def test_autofill_matches_visible_slot_label_to_canonical_seat_id() -> None:
    state = CompPlanState(
        raid_plan_id="plan",
        raid_plan_name="Plan",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(seat_id="tank-1", role="Tank"),
        ),
    )
    candidate = _candidate(
        "tank",
        name="Tank Candidate",
        source_kind="reference_template",
        source_name="Reference",
        eso_class="Dragonknight",
        role="Tank",
        gear_sets=("Lucent Echoes", "Pearlescent Ward"),
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(
            CompTeamCandidatePool(
                slot_name="Tank 1",
                candidates=(candidate,),
            ),
        ),
    )

    chair = result.state.chair("tank-1")
    assert chair is not None
    assert chair.eso_class == "Dragonknight"
    assert chair.planned_gear_sets == ("Lucent Echoes", "Pearlescent Ward")
    assert result.applied_count == 1


def test_autofill_preserves_existing_planned_gear_and_selected_build() -> None:
    state = CompPlanState(
        raid_plan_id="plan",
        raid_plan_name="Plan",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="Jarakeen",
                role="Healer",
                selected_build_name="DF Healer",
                planned_gear_sets=("Spell Power Cure", "Ozezan the Inferno"),
            ),
        ),
    )
    candidate = _candidate(
        "rojo",
        name="RoJo",
        source_name="Jarakeen",
        gear_sets=("Jorvuld's Guidance", "Perfected Roaring Opportunist"),
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(
            CompTeamCandidatePool(
                slot_name="Healer 1",
                candidates=(candidate,),
            ),
        ),
    )

    chair = result.state.chair("healer-1")
    assert chair is not None
    assert chair.selected_build_name == "DF Healer"
    assert chair.planned_gear_sets == ("Spell Power Cure", "Ozezan the Inferno")
    assert result.applied_count == 0
    assert result.skipped_existing == ("healer-1",)


def test_autofill_respects_explicit_build_or_gear_lock() -> None:
    for lock in ("build", "gear"):
        state = CompPlanState(
            raid_plan_id=f"plan-{lock}",
            raid_plan_name="Plan",
            trial_id="Sunspire",
            chairs=(
                CompChairState(
                    seat_id="healer-1",
                    role="Healer",
                    locked_fields=(lock,),
                ),
            ),
        )
        candidate = _candidate("candidate", name="Candidate")

        result = CompPlanAutoFillService().apply(
            state=state,
            pools=(
                CompTeamCandidatePool(
                    slot_name="Healer 1",
                    candidates=(candidate,),
                ),
            ),
        )

        chair = result.state.chair("healer-1")
        assert chair is not None
        assert chair.planned_gear_sets == ()
        assert result.applied_count == 0


def test_open_recruit_receives_planning_evidence_without_fake_player_or_saved_build_binding() -> None:
    state = CompPlanState(
        raid_plan_id="recruit",
        raid_plan_name="Recruit",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-2",
                player_name="",
                role="Healer",
            ),
        ),
    )
    candidate = _candidate(
        "saved:healer",
        name="Sweaty Healer",
        source_name="ActualPlayer",
        gear_sets=("Jorvuld's Guidance", "Perfected Roaring Opportunist"),
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(
            CompTeamCandidatePool(
                slot_name="Healer 2",
                candidates=(candidate,),
            ),
        ),
    )

    chair = result.state.chair("healer-2")
    assert chair is not None
    assert chair.player_name == ""
    assert chair.selected_build_name is None
    assert chair.planned_gear_sets == (
        "Jorvuld's Guidance",
        "Perfected Roaring Opportunist",
    )
    assert chair.candidate_id == "saved:healer"
    assert chair.build_source_name == "ActualPlayer"


def test_named_player_may_bind_matching_saved_build() -> None:
    state = CompPlanState(
        raid_plan_id="named",
        raid_plan_name="Named",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="Jarakeen",
                role="Healer",
            ),
        ),
    )
    candidate = _candidate(
        "saved:magrat",
        name="DF Healer",
        source_name="Jarakeen",
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(
            CompTeamCandidatePool(
                slot_name="Healer 1",
                candidates=(candidate,),
            ),
        ),
    )

    chair = result.state.chair("healer-1")
    assert chair is not None
    assert chair.selected_build_name == "DF Healer"
    assert chair.candidate_id == "saved:magrat"


def test_autofill_prefers_required_provider_coverage_over_higher_relevance() -> None:
    state = CompPlanState(
        raid_plan_id="provider",
        raid_plan_name="Provider",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(seat_id="healer-2", role="Healer"),
        ),
    )
    high_score = _candidate(
        "high",
        name="High Score",
        source_kind="reference_template",
        source_name="Reference",
        score=999.0,
    )
    provider = _candidate(
        "provider",
        name="Provider",
        source_kind="reference_template",
        source_name="Reference",
        score=1.0,
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(
            CompTeamCandidatePool(
                slot_name="Healer 2",
                candidates=(high_score, provider),
                required_provider_ids=("major_slayer",),
            ),
        ),
        provider_ids_by_candidate={
            "high": (),
            "provider": ("major_slayer",),
        },
        required_team_provider_ids=("major_slayer",),
    )

    chair = result.state.chair("healer-2")
    assert chair is not None
    assert chair.candidate_id == "provider"


def test_autofill_does_not_adopt_candidate_skill_package_yet() -> None:
    state = CompPlanState(
        raid_plan_id="skills",
        raid_plan_name="Skills",
        trial_id="Sunspire",
        chairs=(CompChairState(seat_id="dd-1", role="Damage"),),
    )
    base = _candidate(
        "skills-candidate",
        name="Skills Candidate",
        source_kind="reference_template",
        source_name="Reference",
        role="Damage",
    )
    candidate = CompBuildCandidate(
        **{
            **base.__dict__,
            "skills": ("Skill One", "Skill Two"),
        }
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(
            CompTeamCandidatePool(
                slot_name="DD 1",
                candidates=(candidate,),
            ),
        ),
    )

    chair = result.state.chair("dd-1")
    assert chair is not None
    assert chair.planned_skills == ()
