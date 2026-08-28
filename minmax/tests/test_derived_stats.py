from minmax.derived_stats import DerivedStatCalculator, DerivedStatInputs, StatContribution
from minmax.stat_ids import StatId


def test_weapon_damage_uses_level_baseline_and_flat_contributions():
    trace = DerivedStatCalculator().weapon_damage(
        DerivedStatInputs(
            level=50,
            flat=(
                StatContribution("item", 129),
                StatContribution("set", 215),
                StatContribution("mundus", 238),
            ),
        )
    )

    assert trace.raw_value == 1582
    assert trace.final_value == 1582
    assert trace.steps[-1][0] == "ESO rounding"


def test_spell_damage_applies_percentage_modifiers_after_flat_contributions():
    trace = DerivedStatCalculator().spell_damage(
        DerivedStatInputs(
            level=50,
            flat=(StatContribution("item", 300),),
            percent=(
                StatContribution("skill", 0.05),
                StatContribution("buff", 0.10),
            ),
        )
    )

    assert trace.final_value == 1496
    assert trace.raw_value == trace.final_value - 1 + 0.0000000000002


def test_post_percentage_contributions_are_traced_separately():
    trace = DerivedStatCalculator().resolved_stat(
        StatId.CRITICAL_DAMAGE,
        base=0.5,
        inputs=DerivedStatInputs(
            percent=(StatContribution("skill", 0.10),),
            additive_after_percent=(StatContribution("bloodthirsty", 0.05),),
        ),
    )

    assert trace.final_value == 0.65
    assert abs(trace.raw_value - 0.65) < 1e-12
    assert [step[0] for step in trace.steps] == [
        "base",
        "percentage modifiers",
        "bloodthirsty",
        "ESO ratio",
    ]


def test_critical_damage_base_is_50_percent_not_100_percent():
    trace = DerivedStatCalculator().resolved_stat(
        StatId.CRITICAL_DAMAGE,
        base=0.50,
    )

    assert trace.raw_value == 0.50
    assert trace.final_value == 0.50


def test_critical_chance_base_is_10_percent_not_100_percent():
    trace = DerivedStatCalculator().resolved_stat(
        StatId.CRITICAL_CHANCE,
        base=0.10,
    )

    assert trace.raw_value == 0.10
    assert trace.final_value == 0.10


def test_resolved_stat_does_not_invent_an_eso_formula():
    trace = DerivedStatCalculator().resolved_stat(
        StatId.SPELL_PENETRATION,
        base=1000,
        inputs=DerivedStatInputs(
            flat=(StatContribution("item", 500),),
        ),
    )

    assert trace.final_value == 1500
