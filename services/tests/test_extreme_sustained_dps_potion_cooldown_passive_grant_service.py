from minmax.character_progression import CharacterProgression
from services.extreme_sustained_dps_potion_cooldown_passive_grant_service import (
    ExtremeSustainedDPSPotionCooldownPassiveGrantService,
)


class _Universe:
    def __init__(self, rows=()):
        self.rows = tuple(rows)

    def passives(self):
        return self.rows


def test_explicit_empty_rank_inventory_is_complete_empty_grant_inventory() -> None:
    service = ExtremeSustainedDPSPotionCooldownPassiveGrantService(_Universe())

    result = service.resolve(
        object(),
        CharacterProgression(passive_ranks={}),
    )

    assert result == ()


def test_missing_passive_rank_inventory_fails_closed() -> None:
    service = ExtremeSustainedDPSPotionCooldownPassiveGrantService(_Universe())

    try:
        service.resolve(object(), CharacterProgression())
    except ValueError as exc:
        assert "explicit passive ranks" in str(exc)
    else:
        raise AssertionError("missing passive progression must fail closed")
