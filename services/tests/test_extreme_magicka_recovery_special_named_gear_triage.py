from types import SimpleNamespace

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from tools.audit_extreme_magicka_recovery_special_named_gear_triage import (
    SpecialPairTriage,
    _mapped_recovery_obligation,
)


def _evidence(*effects):
    return SimpleNamespace(candidate=SimpleNamespace(source_effects=tuple(effects)))


def test_mapped_conditional_flat_recovery_is_direct_challenger():
    row = _mapped_recovery_obligation(
        _evidence(
            Effect(
                stat=StatId.MAGICKA_RECOVERY,
                operation=EffectOperation.ADD,
                value=465.0,
                unit=EffectUnit.FLAT,
                source="test",
                condition="runtime_condition",
            )
        )
    )

    assert row is not None
    assert row["kind"] == "mapped_conditional_flat"
    assert row["flat"] == 465.0
    assert row["can_raise"] is True


def test_mapped_percent_recovery_preserves_percent_units():
    row = _mapped_recovery_obligation(
        _evidence(
            Effect(
                stat=StatId.MAGICKA_RECOVERY,
                operation=EffectOperation.ADD_PERCENT,
                value=15.0,
                unit=EffectUnit.PERCENT,
                source="test",
                condition="minor_intellect",
            )
        )
    )

    assert row is not None
    assert row["kind"] == "mapped_conditional_percent"
    assert row["percent"] == 15.0
    assert row["condition"] == "minor_intellect"


def test_max_magicka_only_pair_is_bounded_by_enlivening_headroom():
    row = SpecialPairTriage(
        set_id=1,
        set_name="resource-only",
        piece_count=1,
        max_magicka_kind="conditional_flat",
        max_magicka_value=9999.0,
        max_magicka_recovery_ceiling=15.37632,
    )

    assert row.direct_recovery_challenger is False
    assert row.max_magicka_only_challenger is True
    assert row.reviewed_non_challenger is False
