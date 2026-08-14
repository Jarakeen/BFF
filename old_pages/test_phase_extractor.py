from services.uesp.phase_extractor import extract_phases


def main() -> None:
    blocks = [
        {"type": "p", "text": "The boss attacks at 70% health."},
        {"type": "p", "text": "During Phase 2, the boss summons wraiths."},
        {"type": "p", "text": "Phase 2 begins at 70% health."},
        {"type": "p", "text": "At 70% health, the boss uses another ability."},
        {"type": "p", "text": "During Phase 3, the arena changes."},
        {"type": "p", "text": "Phase 3 begins below 40% health."},
    ]

    phases = extract_phases(blocks)
    assert [(p.label, p.threshold) for p in phases] == [
        ("Phase 2", "70%"),
        ("Phase 3", "40%"),
    ], phases

    print("PHASE EXTRACTOR TEST PASSED")
    for phase in phases:
        print(f"  {phase.label}: threshold={phase.threshold!r}")


if __name__ == "__main__":
    main()
