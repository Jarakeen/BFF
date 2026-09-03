from __future__ import annotations

from dataclasses import replace

from minmax.base_character_state import BaseCharacterCalculator
from minmax.build_calculation_context import BuildCalculationContext
from minmax.build_candidate import (
    BuildCandidate,
    BuildChange,
    CandidateEvaluationState,
)
from minmax.build_candidate_context import (
    build_candidate_context,
    progression_for_candidate,
)
from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild


class _RecordingContextFactory:
    def __init__(self, *, unresolved: tuple[str, ...] = ()) -> None:
        self.calls: list[dict] = []
        self.unresolved = unresolved

    def build(self, **kwargs) -> BuildCalculationContext:
        self.calls.append(kwargs)
        progression = kwargs["progression"]
        state = BaseCharacterCalculator().calculate(attributes=progression.attributes)
        return BuildCalculationContext(
            character_id=kwargs["character_id"],
            build_id=kwargs["build_id"],
            progression=progression,
            character_state=state,
            active_bar=kwargs["active_bar"],
            unresolved_gear_effects=self.unresolved,
        )


def _candidate(
    *,
    evaluation_state: CandidateEvaluationState = CandidateEvaluationState.EVALUABLE,
    unresolved: tuple[str, ...] = (),
) -> BuildCandidate:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer Candidate",
        AttributeHealth=10,
        AttributeMagicka=54,
        AttributeStamina=0,
        Mundus="The Thief",
    )
    return BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id="df-healer:mundus:thief",
        candidate_build=build,
        changes=(
            BuildChange.from_values(
                path="Mundus",
                before="The Ritual",
                after="The Thief",
                source="phase12:test",
            ),
        ),
        candidate_source="phase12:test",
        evaluation_state=evaluation_state,
        unresolved=unresolved,
    )


def _baseline_progression() -> CharacterProgression:
    return CharacterProgression(
        attributes=AttributeAllocation(health=64),
        owned_skill_lines=("Restoration Staff", "Light Armor"),
        passive_ranks={"Evocation": 2},
        passive_cp_points={"Rejuvenation": 50},
    )


def test_progression_for_candidate_changes_only_attribute_allocation() -> None:
    baseline = _baseline_progression()

    result = progression_for_candidate(_candidate(), baseline)

    assert result.attributes == AttributeAllocation(health=10, magicka=54, stamina=0)
    assert result.owned_skill_lines == baseline.owned_skill_lines
    assert result.passive_ranks == baseline.passive_ranks
    assert result.passive_cp_points == baseline.passive_cp_points
    assert baseline.attributes == AttributeAllocation(health=64)


def test_build_candidate_context_delegates_to_authoritative_factory() -> None:
    factory = _RecordingContextFactory()
    candidate = _candidate()

    result = build_candidate_context(
        candidate=candidate,
        baseline_progression=_baseline_progression(),
        context_factory=factory,
        active_bar="back",
        target_count=3,
    )

    assert result.resolved
    assert result.context is not None
    assert result.context.character_id == "magrat"
    assert result.context.build_id == "df-healer:mundus:thief"
    assert result.context.progression.attributes == AttributeAllocation(
        health=10,
        magicka=54,
        stamina=0,
    )
    assert len(factory.calls) == 1
    assert factory.calls[0]["build"].Mundus == "The Thief"
    assert factory.calls[0]["active_bar"] == "back"
    assert factory.calls[0]["target_count"] == 3


def test_build_candidate_context_preserves_factory_unresolved_evidence() -> None:
    factory = _RecordingContextFactory(unresolved=("Mundus effect unresolved",))

    result = build_candidate_context(
        candidate=_candidate(),
        baseline_progression=_baseline_progression(),
        context_factory=factory,
    )

    assert not result.resolved
    assert result.context is not None
    assert result.unresolved == ("Mundus effect unresolved",)


def test_build_candidate_context_does_not_evaluate_unknown_candidate() -> None:
    factory = _RecordingContextFactory()
    candidate = _candidate(
        evaluation_state=CandidateEvaluationState.UNKNOWN,
        unresolved=("Candidate source is incomplete",),
    )

    result = build_candidate_context(
        candidate=candidate,
        baseline_progression=_baseline_progression(),
        context_factory=factory,
    )

    assert result.context is None
    assert not result.resolved
    assert result.unresolved == ("Candidate source is incomplete",)
    assert factory.calls == []


def test_candidate_build_reconstruction_keeps_baseline_unmodified() -> None:
    candidate = _candidate()
    baseline = PlayerBuild(Mundus="The Ritual")
    candidate_copy = candidate.candidate_build

    candidate_copy.Mundus = "The Shadow"

    assert candidate.candidate_build.Mundus == "The Thief"
    assert baseline.Mundus == "The Ritual"
