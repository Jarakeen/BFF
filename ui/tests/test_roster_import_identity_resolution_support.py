from pathlib import Path


def test_roster_import_identity_matching_ignores_leading_at_sign():
    source = Path("ui/roster_import_identity_resolution_support.py").read_text(encoding="utf-8")

    assert '.lstrip("@")' in source
    assert "same_class" in source
    assert "len(same_class) == 1" in source
    assert "len(unique_names) == 1" in source
    assert "if candidates:" in source
    assert "Multiple saved characters could own this build" in source


def test_roster_import_generates_concise_character_names_when_no_saved_toon_exists():
    source = Path("ui/roster_import_identity_resolution_support.py").read_text(encoding="utf-8")

    for full_name, shorthand in (
        ("arcanist", "Arc"),
        ("dragonknight", "DK"),
        ("necromancer", "Cro"),
        ("nightblade", "NB"),
        ("sorcerer", "Sorc"),
        ("templar", "Plar"),
        ("warden", "Den"),
    ):
        assert f'"{full_name}": "{shorthand}"' in source

    assert '"tank": "Tnk"' in source
    assert '"healer": "Hlz"' in source
    assert '"damage dealer": "DD"' in source
    assert "_generated_character_name(member)" in source
    assert 'generated = f"{base_name} {suffix}"' in source
    assert "Character name auto-filled as" in source


def test_roster_import_accepts_class_and_role_shorthand_aliases():
    source = Path("ui/roster_import_identity_resolution_support.py").read_text(encoding="utf-8")

    for shorthand, full_name in (
        ("arc", "Arcanist"),
        ("dk", "Dragonknight"),
        ("cro", "Necromancer"),
        ("nb", "Nightblade"),
        ("sorc", "Sorcerer"),
        ("plar", "Templar"),
        ("den", "Warden"),
        ("tnk", "Tank"),
        ("hlz", "Healer"),
        ("dd", "Damage Dealer"),
    ):
        assert f'"{shorthand}": "{full_name}"' in source

    assert "roster_import_workflow._normalize_class = _normalize_class_with_shorthand" in source
    assert "roster_import_workflow._normalize_role = _normalize_role_with_shorthand" in source


def test_roster_import_keeps_personnel_unique_by_gamertag_when_character_differs():
    source = Path("ui/roster_import_identity_resolution_support.py").read_text(encoding="utf-8")

    assert "class _PlayerUniqueRosterImportFacade" in source
    assert "Same gamertag means same person" in source
    assert "target.Team = _merge_team_names" in source
    assert "self._service.update_member(target)" in source
    assert "self.merged_existing_count += 1" in source
    assert "roster_import_workflow.apply_roster_import = apply_roster_import_player_unique" in source
    assert "created_roster_members=max(0, result.created_roster_members - merged)" in source
    assert "updated_roster_members=result.updated_roster_members + merged" in source


def test_roster_import_identity_support_is_installed_after_import_workflow():
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "install_roster_import_identity_resolution_support()" in source
    assert source.index("install_roster_import_support()") < source.index(
        "install_roster_import_identity_resolution_support()"
    )
