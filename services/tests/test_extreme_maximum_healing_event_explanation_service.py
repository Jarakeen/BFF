from types import SimpleNamespace

from minmax.skill_component_classification import HealRecipientScope, HealTemporalScope
from models.build_model import PlayerBuild
from services.extreme_maximum_healing_event_class_route_catalog_service import (
    ExtremeMaximumHealingEventClassRouteCatalogService,
)
from services.extreme_maximum_healing_event_explanation_service import (
    ExtremeMaximumHealingEventExplanationService,
    ExtremeMaximumHealingEventTrace,
)


class _Components:
    def get_for_skill_rank(self, _skill_rank_id):
        return (
            SimpleNamespace(
                coefficient_number=3,
                can_crit=True,
                heal_recipient_scope=HealRecipientScope.GROUP,
                heal_recipient_key="friendly_targets",
                heal_event_key="pet_special_activation",
                heal_temporal_scope=HealTemporalScope.DIRECT,
            ),
            SimpleNamespace(
                coefficient_number=4,
                can_crit=True,
                heal_recipient_scope=HealRecipientScope.PET,
                heal_recipient_key="summoned_pet",
                heal_event_key="pet_special_activation",
                heal_temporal_scope=HealTemporalScope.DIRECT,
            ),
        )


class _Scoring:
    def score(self, **_kwargs):
        return SimpleNamespace(
            critical_winner_coefficients=(3,),
            unresolved=(),
        )


def _ordinary_unified_entry():
    event = SimpleNamespace(
        normal_heal=10000.0,
        critical_heal=15000.0,
        critical_multiplier=1.5,
        heal_coefficient_numbers=(3, 4),
        tooltip_result=SimpleNamespace(
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=3, output_value=8000.0),
                SimpleNamespace(coefficient_number=4, output_value=4000.0),
            ),
            components=(),
        ),
    )
    route_entry = SimpleNamespace(
        candidate=SimpleNamespace(skill_rank_id=4847),
        optimization=SimpleNamespace(optimized_event=event),
    )
    return SimpleNamespace(
        source_kind="ordinary_skill",
        route_entry=route_entry,
    )


def test_ordinary_explanation_recovers_critical_winner_recipient_event_identity():
    healing_events = SimpleNamespace(
        tooltip_service=SimpleNamespace(components=_Components()),
        event_group_scoring=_Scoring(),
    )
    trace = ExtremeMaximumHealingEventExplanationService(
        healing_events=healing_events
    ).describe(_ordinary_unified_entry())

    assert trace.coefficient_numbers == (3,)
    assert trace.recipient_scopes == ("group",)
    assert trace.recipient_keys == ("friendly_targets",)
    assert trace.event_keys == ("pet_special_activation",)
    assert trace.temporal_scopes == ("direct",)
    assert trace.unresolved == ()


def test_blood_magic_explanation_uses_explicit_reviewed_self_trigger_identity():
    trace = ExtremeMaximumHealingEventExplanationService().describe(
        SimpleNamespace(source_kind="blood_magic")
    )

    assert trace.coefficient_numbers == ()
    assert trace.recipient_scopes == ("self",)
    assert trace.recipient_keys == ("caster",)
    assert trace.event_keys == ("blood_magic_costed_dark_magic_trigger",)
    assert trace.temporal_scopes == ("direct",)


class _Catalog:
    def __init__(self, result):
        self.result = result

    def rank(self, _build, **_kwargs):
        return self.result


class _Explanation:
    def describe(self, entry):
        if entry.source_kind == "blood_magic":
            return ExtremeMaximumHealingEventTrace(
                recipient_scopes=("self",),
                recipient_keys=("caster",),
            )
        return ExtremeMaximumHealingEventTrace(
            recipient_scopes=("group",),
            recipient_keys=("friendly_targets",),
        )


def _route():
    return SimpleNamespace(
        equipped_skill_lines=("dark_magic", "daedric_summoning", "storm_calling")
    )


def _ordinary_entry():
    return SimpleNamespace(
        route=_route(),
        candidate=SimpleNamespace(name="Twilight Matriarch"),
        slotted_index=1,
        optimization=SimpleNamespace(
            optimized_event=SimpleNamespace(critical_heal=15000.0)
        ),
        mechanic_complete=True,
        unresolved=(),
    )


def _blood_entry():
    return SimpleNamespace(
        route=_route(),
        trigger=SimpleNamespace(name="Dark Exchange"),
        slotted_index=2,
        normal_heal=18000.0,
        mechanic_complete=True,
        unresolved=(),
    )


def _result(entries):
    return SimpleNamespace(
        entries=tuple(entries),
        best_scored=None,
        best_complete=None,
        search_scope=(),
        omitted_scope=(),
    )


def test_unified_winner_explanation_reports_source_route_trace_runner_up_and_margin():
    result = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=_Catalog(_result((_ordinary_entry(),))),
        blood_magic=_Catalog(_result((_blood_entry(),))),
        explanations=_Explanation(),
    ).rank(PlayerBuild(Name="Test", BuildName="Explain", EsoClass="sorcerer"))

    explanation = result.winner_explanation
    assert explanation is not None
    assert explanation.source_kind == "blood_magic"
    assert explanation.source_name == "Blood Magic via Dark Exchange"
    assert explanation.event_kind == "normal_noncritical"
    assert explanation.event_value == 18000.0
    assert explanation.route_skill_lines == (
        "dark_magic",
        "daedric_summoning",
        "storm_calling",
    )
    assert explanation.slotted_index == 2
    assert explanation.trace.recipient_keys == ("caster",)
    assert explanation.runner_up_name == "Twilight Matriarch"
    assert explanation.runner_up_value == 15000.0
    assert explanation.margin == 3000.0
    assert "exceeding Twilight Matriarch" in explanation.reason
    assert "3000.000" in explanation.reason
