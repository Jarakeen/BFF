from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_plan_skill_seed_service import CompPlanSkillSeedService


def _state(*, planned_skills=(), locked_fields=()) -> CompPlanState:
    return CompPlanState(
        raid_plan_id="plan",
        raid_plan_name="Plan",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="Healer",
                planned_skills=planned_skills,
                locked_fields=locked_fields,
            ),
        ),
    )


def _candidate(
    *,
    source_kind="saved_build",
    complete_build=True,
    skills=("Combat Prayer", "Energy Orb"),
) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id="candidate",
        name="DF Healer",
        source_kind=source_kind,
        source_name="Magrat",
        source_url="",
        eso_class="Warden",
        role="Healer",
        gear_sets=("Set A", "Set B"),
        skills=skills,
        mundus="The Ritual",
        complete_build=complete_build,
        unresolved=(),
        score=100.0,
        score_reasons=("reviewed candidate",),
    )


def test_saved_build_can_seed_an_empty_skill_plan() -> None:
    service = CompPlanSkillSeedService()
    state = _state()
    candidate = _candidate()

    proposal = service.propose(
        state=state,
        seat_id="healer-1",
        candidate=candidate,
    )
    updated, applied = service.apply(
        state=state,
        seat_id="healer-1",
        candidate=candidate,
        proposal=proposal,
    )

    assert proposal.eligible is True
    assert proposal.skills == ("Combat Prayer", "Energy Orb")
    assert applied == proposal
    chair = updated.chair("healer-1")
    assert chair is not None
    assert chair.planned_skills == ("Combat Prayer", "Energy Orb")


def test_existing_planned_skills_are_never_replaced() -> None:
    service = CompPlanSkillSeedService()
    state = _state(planned_skills=("Budding Seeds",))
    candidate = _candidate()

    proposal = service.propose(
        state=state,
        seat_id="healer-1",
        candidate=candidate,
    )
    updated, result = service.apply(
        state=state,
        seat_id="healer-1",
        candidate=candidate,
        proposal=proposal,
    )

    assert proposal.eligible is False
    assert "preserved" in proposal.reason
    assert updated == state
    assert updated.chair("healer-1").planned_skills == ("Budding Seeds",)
    assert result == proposal


def test_skills_lock_blocks_seed_even_when_skill_plan_is_empty() -> None:
    service = CompPlanSkillSeedService()
    state = _state(locked_fields=("skills",))
    proposal = service.propose(
        state=state,
        seat_id="healer-1",
        candidate=_candidate(),
    )

    assert proposal.eligible is False
    assert proposal.reason == "Skills are locked for this chair."


def test_incomplete_reference_template_remains_suggestion_only() -> None:
    proposal = CompPlanSkillSeedService().propose(
        state=_state(),
        seat_id="healer-1",
        candidate=_candidate(
            source_kind="reference_template",
            complete_build=False,
        ),
    )

    assert proposal.eligible is False
    assert "incomplete" in proposal.reason


def test_complete_reference_template_can_seed_empty_skills() -> None:
    proposal = CompPlanSkillSeedService().propose(
        state=_state(),
        seat_id="healer-1",
        candidate=_candidate(
            source_kind="reference_template",
            complete_build=True,
        ),
    )

    assert proposal.eligible is True


def test_noncanonical_observation_source_is_evidence_only() -> None:
    proposal = CompPlanSkillSeedService().propose(
        state=_state(),
        seat_id="healer-1",
        candidate=_candidate(
            source_kind="esologs_observed",
            complete_build=True,
        ),
    )

    assert proposal.eligible is False
    assert "evidence-only" in proposal.reason
