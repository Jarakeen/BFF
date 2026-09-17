from __future__ import annotations

from minmax.gear_sets import GearSet, GearSetBonus
from services.extreme_invisibility_gear_provider_service import (
    ExtremeInvisibilityGearProviderService,
)


class _Repository:
    def __init__(self, description: str | None):
        self.description = description

    def get_set(self, name: str):
        assert name == "Prowler's Talisman"
        if self.description is None:
            return None
        return GearSet(id=77, name=name, category="standard", max_equip_count=1)

    def get_bonuses(self, set_id: int):
        assert set_id == 77
        return [
            GearSetBonus(
                id=1,
                set_id=77,
                piece_count=1,
                description=self.description or "",
            )
        ]


_DESCRIPTION = (
    "(1 item) While Battle Spirit is inactive, bracing while crouching turns you invisible for 10 seconds. "
    "This can occur once every 45 seconds. Increase your chances of successfully Pickpocketing by 5%. "
    "On dealing Critical Damage, increase your Max Magicka and Max Stamina for 10 seconds, up to 1900 at 10 stacks. "
    "On dealing non-Critical Damage, increase your Health, Magicka, and Stamina Recovery for 10 seconds, up to 160 at 10 stacks. "
    "Either effect can occur up to once every 1 second. Talisman upgrades: 0"
)


def test_prowlers_talisman_extracts_reviewed_duration_and_cooldown() -> None:
    service = ExtremeInvisibilityGearProviderService(
        "unused.db",
        repository=_Repository(_DESCRIPTION),
    )

    providers = service.reviewed_providers()

    assert len(providers) == 1
    row = providers[0]
    assert row.name == "Prowler's Talisman"
    assert row.entity_id == "prowlers_talisman"
    assert row.duration_seconds == 10.0
    assert row.cooldown_seconds == 45.0
    assert "10s invisibility" in row.evidence[0]
    assert "45s" in row.evidence[1]


def test_catalog_exposes_reviewed_provider_but_keeps_global_denominator_open() -> None:
    service = ExtremeInvisibilityGearProviderService(
        "unused.db",
        repository=_Repository(_DESCRIPTION),
    )

    catalog = service.catalog()

    assert len(catalog.verified) == 1
    assert catalog.verified[0].duration_seconds == 10.0
    assert catalog.denominator_proven is False
    assert catalog.unresolved == (
        "Invisibility provider corpus is not yet exhaustive across skills, potions, and other legal sources",
    )


def test_description_drift_fails_closed_instead_of_guessing_runtime_semantics() -> None:
    service = ExtremeInvisibilityGearProviderService(
        "unused.db",
        repository=_Repository(
            _DESCRIPTION.replace("once every 45 seconds", "periodically")
        ),
    )

    assert service.reviewed_providers() == ()
    catalog = service.catalog()
    assert catalog.verified == ()
    assert catalog.denominator_proven is False


def test_missing_set_produces_no_fake_provider() -> None:
    service = ExtremeInvisibilityGearProviderService(
        "unused.db",
        repository=_Repository(None),
    )

    assert service.reviewed_providers() == ()
