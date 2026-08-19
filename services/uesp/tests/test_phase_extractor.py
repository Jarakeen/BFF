from services.uesp.phase_extractor import extract_phases


def test_phase_label_and_threshold_from_same_prose_block():
    phases = extract_phases([
        {
            "type": "p",
            "text": "The fight has three phases. Phase 2 begins when the boss reaches 70% health.",
        }
    ])
    assert len(phases) == 1
    assert phases[0].label == "Phase 2"
    assert phases[0].threshold == "70%"


def test_bare_health_threshold_does_not_create_phase():
    phases = extract_phases([
        {"type": "p", "text": "At 40% health the boss becomes more aggressive."}
    ])
    assert phases == []
