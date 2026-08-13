from services.uesp.mechanic_classifier import classify_mechanic


def main() -> None:
    sludge = classify_mechanic(
        "Noxious Sludge",
        "Oaxiltso retches poison on two targets. Poisoned targets drop Noxious Pools "
        "until they cleanse the effect by walking into the pools.",
    )
    assert sludge.damage_type == "poison"
    assert sludge.target_count == 2
    assert sludge.requires_cleanse is True
    assert sludge.persistent_hazard is True
    assert sludge.requires_movement is True

    blitz = classify_mechanic(
        "Savage Blitz",
        "Oaxiltso charges forward and chomps the farthest target. This can and should "
        "be dodged by the target and everyone on his path.",
    )
    assert blitz.damage_type == "physical"
    assert blitz.requires_movement is True
    assert blitz.requires_positioning is True
    assert blitz.interruptible is None

    explicit_interrupt = classify_mechanic(
        "Interruptible Attack",
        "The ability is interruptible and deals physical damage.",
    )
    assert explicit_interrupt.interruptible is True

    print("MECHANIC CLASSIFIER TEST PASSED")
    print("  sludge: poison / 2 targets / cleanse / persistent hazard")
    print("  blitz: physical / movement / positioning / no inferred interrupt")
    print("  explicit interrupt: true")


if __name__ == "__main__":
    main()
