from services.rotation_healer_u50_periodic_reapplication_repository import (
    RotationHealerPeriodicReapplicationKind,
    RotationHealerU50PeriodicReapplicationRepository,
)


def test_budding_seeds_second_activation_is_not_generic_restart():
    item = RotationHealerU50PeriodicReapplicationRepository().get(
        source_name="Budding Seeds",
        coefficient_number=2,
    )

    assert item is not None
    assert item.kind is RotationHealerPeriodicReapplicationKind.SECOND_ACTIVATION_SPECIAL
    assert "bloom" in item.note.casefold()
    assert item.provenance


def test_illustrious_healing_is_one_active_instance_without_fake_boundary():
    item = RotationHealerU50PeriodicReapplicationRepository().get(
        source_name="Illustrious Healing",
        coefficient_number=1,
    )

    assert item is not None
    assert item.kind is RotationHealerPeriodicReapplicationKind.ONE_ACTIVE_INSTANCE
    assert "boundary" in item.note.casefold()
    assert any("Update 23" in source for source in item.provenance)


def test_energy_orb_is_one_active_instance_without_fake_boundary():
    item = RotationHealerU50PeriodicReapplicationRepository().get(
        source_name="Energy Orb",
        coefficient_number=1,
    )

    assert item is not None
    assert item.kind is RotationHealerPeriodicReapplicationKind.ONE_ACTIVE_INSTANCE
    assert "boundary" in item.note.casefold()
    assert any("Update 23" in source for source in item.provenance)


def test_echoing_vigor_reapplication_remains_unresolved():
    assert (
        RotationHealerU50PeriodicReapplicationRepository().get(
            source_name="Echoing Vigor",
            coefficient_number=1,
        )
        is None
    )
