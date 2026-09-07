from __future__ import annotations

from services.extreme_buff_context_explanation_service import (
    ExtremeBuffContextExplanationService,
)
from services.named_buff_resolution_service import NamedBuffContribution


def _major_sorcery_potion():
    return NamedBuffContribution(
        stacking_key="major_sorcery",
        objective_key="spell_damage",
        projected_delta=1000.0,
        source="Essence of Spell Power: Major Sorcery",
        source_kind="potion",
    )


def test_explanation_reports_redundant_major_sorcery_skill():
    result = ExtremeBuffContextExplanationService.explain_build(
        ("Tome-Bearer's Inspiration",),
        (),
        "spell_damage",
        active_bar="front",
        reference_value=5000.0,
        external_effects=(_major_sorcery_potion(),),
    )

    assert result.marginal_delta == 0.0
    assert result.has_redundancy is True
    assert len(result.suppression_notes) == 1
    assert "major sorcery" in result.suppression_notes[0].casefold()
    assert "does not stack" in result.suppression_notes[0]


def test_explanation_keeps_major_value_when_only_minor_is_external():
    minor = NamedBuffContribution(
        stacking_key="minor_sorcery",
        objective_key="spell_damage",
        projected_delta=500.0,
        source="Group provider: Minor Sorcery",
        source_kind="group_provider",
    )

    result = ExtremeBuffContextExplanationService.explain_build(
        ("Tome-Bearer's Inspiration",),
        (),
        "spell_damage",
        active_bar="back",
        reference_value=5000.0,
        external_effects=(minor,),
    )

    assert result.marginal_delta == 1000.0
    assert result.has_redundancy is False
    assert result.suppression_notes == ()
