from types import SimpleNamespace
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

    assert result.complete
    assert result.passives == ()
    assert result.unresolved == ()


def test_missing_passive_rank_inventory_fails_closed() -> None:
    service = ExtremeSustainedDPSPotionCooldownPassiveGrantService(_Universe())

    try:
        service.resolve(object(), CharacterProgression())
    except ValueError as exc:
        assert "explicit passive ranks" in str(exc)
    else:
        raise AssertionError("missing passive progression must fail closed")



def test_owned_unreviewed_potion_cooldown_passive_fails_closed() -> None:
    passive = SimpleNamespace(
        name="Suspicious Passive",
        skill_line="Alchemy",
        description="Reduces the cooldown of potions by an amount not yet reviewed.",
    )
    service = ExtremeSustainedDPSPotionCooldownPassiveGrantService(
        _Universe((passive,))
    )

    try:
        service.resolve(
            object(),
            CharacterProgression(passive_ranks={"Suspicious Passive": 1}),
        )
    except ValueError as exc:
        assert "unreviewed potion cooldown semantics" in str(exc)
    else:
        raise AssertionError("unreviewed owned potion cooldown passive must fail closed")
