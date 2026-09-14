from services.service_catalog import canonical_service_for


def test_roster_player_identity_service_is_cataloged_as_explicit_identity_workflow() -> None:
    alias_service = canonical_service_for("roster_player_alias_history")
    merge_service = canonical_service_for("roster_player_identity_merge")

    assert alias_service is not None
    assert alias_service.service_id == "team.roster.player_identity"
    assert merge_service is not None
    assert merge_service.service_id == "team.roster.player_identity"
    assert "never infers" in alias_service.notes
