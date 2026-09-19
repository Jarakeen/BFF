from types import SimpleNamespace

from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_candidate_adviser_service import CompCandidateAdviserService


def _candidate(
    candidate_id: str,
    *,
    name: str = "Candidate",
    gear_sets: tuple[str, ...] = (),
    eso_class: str = "",
    mundus: str = "",
    source_kind: str = "reference_template",
    source_name: str = "Reference",
) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id=candidate_id,
        name=name,
        source_kind=source_kind,
        source_name=source_name,
        source_url="",
        eso_class=eso_class,
        role="Healer",
        gear_sets=gear_sets,
        skills=(),
        mundus=mundus,
        complete_build=False,
        unresolved=(),
        score=100.0,
        score_reasons=("reviewed candidate",),
        five_piece_sets=gear_sets,
    )


def test_rojo_improves_major_slayer_evidence_without_inventing_new_plan_coverage(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (
            SimpleNamespace(
                source_name="Roaring Opportunist",
                effect_key="major_slayer",
            ),
        ),
    )

    state = CompPlanState(
        raid_plan_id="plan",
        raid_plan_name="Plan",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(
                seat_id="healer-2",
                player_name="Healer",
                primary_assignment="Major Slayer",
            ),
        ),
    )
    candidate = _candidate(
        "rojo",
        name="RoJo Healer",
        gear_sets=("Jorvuld's Guidance", "Perfected Roaring Opportunist"),
    )

    proposal = CompCandidateAdviserService(tmp_path / "eso.db").evaluate(
        state=state,
        seat_id="healer-2",
        candidate=candidate,
    )

    assert "Major Slayer" not in proposal.gained_planned_required
    assert "Major Slayer" in proposal.gained_effect_evidence
    assert "Major Slayer" in proposal.assignment_proof_improved
    assert proposal.lost_planned_required == ()


def test_locked_build_does_not_block_unlocked_gear_change(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (),
    )

    state = CompPlanState(
        raid_plan_id="plan",
        raid_plan_name="Plan",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="Healer",
                selected_build_name="Keep This Build",
                planned_gear_sets=("Old Set",),
                locked_fields=("build",),
            ),
        ),
    )
    candidate = _candidate(
        "new-gear",
        name="Different Build Name",
        gear_sets=("New Set A", "New Set B"),
    )

    service = CompCandidateAdviserService(tmp_path / "eso.db")
    proposal = service.evaluate(
        state=state,
        seat_id="healer-1",
        candidate=candidate,
    )
    updated, applied = service.apply(
        state=state,
        seat_id="healer-1",
        candidate=candidate,
    )

    assert proposal.applicable is True
    assert "build" in proposal.blocked_fields
    assert "planned_gear_sets" in proposal.changed_fields
    chair = updated.chair("healer-1")
    assert chair is not None
    assert chair.selected_build_name == "Keep This Build"
    assert chair.planned_gear_sets == ("New Set A", "New Set B")
    assert applied.blocked_fields == ("build",)


def test_adviser_reports_duplicate_effect_change(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (
            SimpleNamespace(
                source_name="Spell Power Cure",
                effect_key="major_courage",
            ),
            SimpleNamespace(
                source_name="Vestment of Olorime",
                effect_key="major_courage",
            ),
        ),
    )

    state = CompPlanState(
        raid_plan_id="plan",
        raid_plan_name="Plan",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="H1",
                planned_gear_sets=("Spell Power Cure",),
            ),
            CompChairState(
                seat_id="healer-2",
                player_name="H2",
            ),
        ),
    )
    candidate = _candidate(
        "olorime",
        name="Olorime",
        gear_sets=("Vestment of Olorime",),
    )

    proposal = CompCandidateAdviserService(tmp_path / "eso.db").evaluate(
        state=state,
        seat_id="healer-2",
        candidate=candidate,
    )

    assert "Major Courage" in proposal.duplicates_added
