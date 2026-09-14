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


def test_roster_import_accepts_short_role_aliases():
    source = Path("ui/roster_import_identity_resolution_support.py").read_text(encoding="utf-8")

    assert '"tnk": "Tank"' in source
    assert '"hlz": "Healer"' in source
    assert '"dd": "Damage Dealer"' in source
    assert "roster_import_workflow._normalize_role = _normalize_role_with_shorthand" in source


def test_roster_import_identity_support_is_installed_after_import_workflow():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_roster_import_identity_resolution_support()" in source
    assert source.index("install_roster_import_support()") < source.index(
        "install_roster_import_identity_resolution_support()"
    )
