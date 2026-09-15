from pathlib import Path


def test_context_variant_import_support_replaces_prior_team_imports() -> None:
    source = Path("ui/roster_import_context_variant_support.py").read_text(encoding="utf-8")

    assert "Imported from roster" in source
    assert "selected_players" in source
    assert "builds.before-roster-reimport.json" in source
    assert "characters.before-roster-reimport.json" in source
    assert "consolidate_member_builds" in source
    assert "resolve_import_characters_with_personnel_priority" in source


def test_context_variant_import_support_installs_after_alias_normalization() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert source.index("install_roster_gear_set_alias_import_support()") < source.index(
        "install_roster_import_context_variant_support()"
    )
    assert source.index("install_roster_import_context_variant_support()") < source.index(
        "install_roster_import_match_preview_support()"
    )
