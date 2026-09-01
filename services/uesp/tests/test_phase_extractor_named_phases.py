from services.uesp.phase_extractor import extract_phases


def test_recovers_named_phases_from_dialogue_style_source_text():
    blocks = [
        {
            "type": "p",
            "text": "End of abomination phase (enter behemoth phase)",
        }
    ]

    phases = extract_phases(blocks)
    labels = {phase.label for phase in phases}

    assert "Abomination Phase" in labels
    assert "Behemoth Phase" in labels


def test_deduplicates_repeated_numbered_phase_references():
    blocks = [
        {
            "type": "p",
            "text": "Phase 2 begins when the boss reaches 70% health.",
        },
        {
            "type": "p",
            "text": "During phase 2 the arena floor becomes unsafe.",
        },
        {
            "type": "p",
            "text": "Phase 3 begins later in the fight.",
        },
        {
            "type": "p",
            "text": "During phase 3 meteors are also present.",
        },
    ]

    phases = extract_phases(blocks)

    assert [phase.label for phase in phases] == ["Phase 2", "Phase 3"]
    assert phases[0].threshold == "70%"


def test_health_threshold_add_spawns_do_not_become_phases():
    blocks = [
        {
            "type": "dd",
            "text": (
                "At 90%/75%/50%/25% health, Oaxiltso howls to Mehrunes Dagon "
                "for aid and summons a Havocrel Annihilator."
            ),
        }
    ]

    assert extract_phases(blocks) == []
