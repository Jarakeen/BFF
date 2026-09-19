from pathlib import Path


def test_live_raid_uses_compact_field_console_card_roles() -> None:
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    for role in ("hero", "spots", "callouts", "timeline", "notes", "coverage", "recent"):
        assert f'"{role}"' in source

    assert 'setProperty("liveRaidCard", True)' in source
    assert 'setProperty("liveRaidStatusTile", True)' in source
    assert 'setProperty("liveRaidRosterTable", True)' in source
    assert 'setProperty("liveRaidCalloutText", True)' in source
    assert 'setProperty("liveRaidTimelineText", True)' in source
    assert 'setProperty("liveRaidEventText", True)' in source


def test_live_raid_run_sheet_is_the_only_parchment_card_in_runtime_row() -> None:
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    notes = source.split('FoundryCard("Quick Notes / Run Sheet"', 1)[1].split(
        'FoundryCard("Coverage Snapshot"', 1
    )[0]
    assert 'notes.setProperty("foundryNoteCard", True)' in notes
    assert 'setProperty("parchmentEditor", True)' in notes

    for title in ("Next 60 Seconds", "Coverage Snapshot", "Recent Events"):
        section = source.split(f'FoundryCard("{title}"', 1)[1].split("lower.addWidget", 1)[0]
        assert 'setProperty("foundryNoteCard", True)' not in section


def test_live_raid_status_does_not_claim_unobserved_alive_or_phase_state() -> None:
    source = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")

    assert 'self.alive_label.setText(f"{len(plan.members)} planned")' in source
    assert '"Planned encounter context"' in source
    assert "OBSERVED = external telemetry (not connected)" in source
    assert "11/12 Alive" not in source


def test_urban_wilderness_styles_live_raid_cards_without_flash_or_animation() -> None:
    source = Path("ui/theme/theme_manager.py").read_text(encoding="utf-8")

    assert 'QFrame[liveRaidCard="true"]' in source
    assert 'QFrame[liveRaidCardRole="notes"]' in source
    assert 'QLabel[liveRaidStatusValue="true"][liveRaidStatusRole="timer"]' in source
    assert 'QTableWidget[liveRaidRosterTable="true"]' in source
    assert 'QLabel[liveRaidCalloutText="true"]' in source

    live = source.split("/* Live Raid: dense nocturnal field-console treatment. */", 1)[1]
    assert "animation:" not in live
    assert "qproperty-" not in live
