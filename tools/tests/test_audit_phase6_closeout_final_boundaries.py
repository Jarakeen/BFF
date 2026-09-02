from types import SimpleNamespace

from tools import audit_phase6_closeout as audit
from tools.audit_phase6_component_gaps import Phase6GapRow


def _item(fragment: str, *, coefficient_number: int = 1, signals=("conditional_candidate",)):
    gap = Phase6GapRow(
        skill_rank_id=1,
        coefficient_number=coefficient_number,
        ability_id=10,
        name="Example",
        phase3_reasons=("effect_kind",),
        disposition="richer_component_semantics",
        signals=tuple(signals),
        linked_effects=(),
        named_combat_effects=(),
        fragment=fragment,
    )
    return SimpleNamespace(gap=gap, is_covered=False)


def test_calls_upon_periodic_storm_is_phase7_cadence_not_condition():
    status, _ = audit._closeout_status(
        _item("The atronach calls upon a lightning storm every 2 seconds, dealing $1 Shock Damage to enemies around it.")
    )
    assert status == "PHASE7_BOUNDARY"


def test_while_field_grows_periodic_heal_is_phase7_state_and_cadence():
    status, _ = audit._closeout_status(
        _item("While the field grows, you and allies are healed for $1 Health every 1 second.", signals=("healing_candidate", "conditional_candidate"))
    )
    assert status == "PHASE7_BOUNDARY"


def test_repeated_colossus_smash_is_phase7_cadence():
    status, _ = audit._closeout_status(
        _item("The Colossus smashes the ground three times over 3 seconds, dealing $1 Frost Damage with each smash.", signals=())
    )
    assert status == "PHASE7_BOUNDARY"


def test_neighboring_shield_owns_interrupt_immunity():
    status, reason = audit._closeout_status(
        _item(
            "Channel a beam for up to 4 seconds, dealing $1 Magic Damage every 0.3 seconds, "
            "and gain a damage shield that absorbs up to $2 damage and grants interrupt immunity.",
            signals=("shield_candidate",),
        )
    )
    assert status == "OWNERSHIP_NEGATIVE"
    assert "shield" in reason
