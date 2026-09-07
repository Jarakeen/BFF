from __future__ import annotations

from services.named_buff_resolution_service import (
    NamedBuffContribution,
    NamedBuffResolutionService,
)


def test_duplicate_major_buff_collapses_across_source_kinds():
    effects = (
        NamedBuffContribution(
            stacking_key="Major Sorcery",
            objective_key="spell_damage",
            projected_delta=1000.0,
            source="Tome-Bearer's Inspiration",
            source_kind="skill",
        ),
        NamedBuffContribution(
            stacking_key="major_sorcery",
            objective_key="spell_damage",
            projected_delta=1000.0,
            source="Essence of Spell Power",
            source_kind="potion",
        ),
    )

    selected = NamedBuffResolutionService.resolve(effects)

    assert len(selected) == 1
    assert selected[0].projected_delta == 1000.0


def test_major_and_minor_variants_stack_for_same_stat():
    effects = (
        NamedBuffContribution(
            stacking_key="major_sorcery",
            objective_key="spell_damage",
            projected_delta=1000.0,
            source="Major source",
        ),
        NamedBuffContribution(
            stacking_key="minor_sorcery",
            objective_key="spell_damage",
            projected_delta=500.0,
            source="Minor source",
        ),
    )

    score, sources = NamedBuffResolutionService.score(
        effects,
        objective_key="spell_damage",
    )

    assert score == 1500.0
    assert len(sources) == 2


def test_same_named_buff_can_contribute_to_multiple_objectives():
    effects = (
        NamedBuffContribution(
            stacking_key="minor_resolve",
            objective_key="physical_resistance",
            projected_delta=2974.0,
            source="Bound Aegis",
        ),
        NamedBuffContribution(
            stacking_key="minor_resolve",
            objective_key="spell_resistance",
            projected_delta=2974.0,
            source="Bound Aegis",
        ),
    )

    selected = NamedBuffResolutionService.resolve(effects)

    assert len(selected) == 2
    assert {effect.objective_key for effect in selected} == {
        "physical_resistance",
        "spell_resistance",
    }


def test_duplicate_identity_keeps_largest_reviewed_contribution():
    effects = (
        NamedBuffContribution(
            stacking_key="major_sorcery",
            objective_key="spell_damage",
            projected_delta=900.0,
            source="weaker stale evidence",
        ),
        NamedBuffContribution(
            stacking_key="major_sorcery",
            objective_key="spell_damage",
            projected_delta=1000.0,
            source="canonical current evidence",
        ),
    )

    selected = NamedBuffResolutionService.resolve(effects)

    assert len(selected) == 1
    assert selected[0].projected_delta == 1000.0
    assert selected[0].source == "canonical current evidence"


def test_objective_filter_does_not_mix_unrelated_stats():
    effects = (
        NamedBuffContribution(
            stacking_key="major_sorcery",
            objective_key="spell_damage",
            projected_delta=1000.0,
            source="power",
        ),
        NamedBuffContribution(
            stacking_key="minor_resolve",
            objective_key="physical_resistance",
            projected_delta=2974.0,
            source="armor",
        ),
    )

    score, sources = NamedBuffResolutionService.score(
        effects,
        objective_key="spell_damage",
    )

    assert score == 1000.0
    assert sources == ("power",)
