from services.service_catalog import EvidenceClass, canonical_service_for, get_service


def test_antiquity_service_keeps_reference_and_profile_progress_distinct():
    service = canonical_service_for("antiquity_reference_and_profile_progress")

    assert service is not None
    assert service.service_id == "collectible.antiquity.progress"
    assert service.evidence_class is EvidenceClass.MIXED
    assert "expected harvested row count" in service.notes
    assert "profile progress never rewrites" in service.notes


def test_expedition_is_transient_session_state_not_archive_or_encounter_truth():
    service = canonical_service_for("active_expedition_session_state")

    assert service is not None
    assert service.service_id == "broadcast.expedition.session_state"
    assert "transient active-session state" in service.notes
    assert "not durable archive persistence" in service.notes
    assert "not canonical encounter truth" in service.notes


def test_raid_progress_records_session_events_without_promoting_them_to_mechanics():
    service = canonical_service_for("active_raid_progress_event_recording")

    assert service is not None
    assert service.service_id == "broadcast.raid.progress_events"
    assert service.dependencies == ("broadcast.expedition.session_state",)
    assert "session observations supplied by the caller" in service.notes
    assert "not encounter mechanics" in service.notes


def test_top_team_is_observed_ranked_log_evidence_not_optimal_comp_truth():
    service = canonical_service_for("esologs_top_team_observed_build_evidence")

    assert service is not None
    assert service.service_id == "logs.top_team.observed_build_evidence"
    assert service.evidence_class is EvidenceClass.OBSERVATIONAL
    assert "not canonical optimal composition" in service.notes
    assert "must not be promoted into game-mechanic truth" in service.notes


def test_skill_choice_numeric_ids_never_replace_semantic_skill_identity():
    service = canonical_service_for("skill_bar_choice_reference_projection")

    assert service is not None
    assert service.service_id == "build.skill_choice.reference"
    assert service.evidence_class is EvidenceClass.GAME_MECHANIC
    assert "numeric ability ids" in service.notes
    assert "aliases/evidence only" in service.notes
    assert "lower_snake_case skill identity" in service.notes


def test_application_services_remain_separate_capabilities():
    ids = {
        get_service("collectible.antiquity.progress").service_id,
        get_service("broadcast.expedition.session_state").service_id,
        get_service("broadcast.raid.progress_events").service_id,
        get_service("logs.top_team.observed_build_evidence").service_id,
        get_service("build.skill_choice.reference").service_id,
    }

    assert ids == {
        "collectible.antiquity.progress",
        "broadcast.expedition.session_state",
        "broadcast.raid.progress_events",
        "logs.top_team.observed_build_evidence",
        "build.skill_choice.reference",
    }
