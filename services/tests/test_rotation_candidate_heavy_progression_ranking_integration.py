from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.character_progression import CharacterProgression
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_heavy_sustain_ranking_service import (
    RotationCandidateHeavySustainInput,
    RotationCandidateHeavySustainRankingService,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingResult,
    RotationCandidateTier,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)


def _slots() -> tuple[SlottedSkill, ...]:
    return tuple(
        SlottedSkill(
            skill_id=f"dummy_{index}",
            skill_line_id="fighters_guild",
            is_ultimate=index == 5,
        )
        for index in range(6)
    )


def _bar(bar_id: BarId, weapon: WeaponType) -> Bar:
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon),
        off_hand=None,
        slots=_slots(),
    )


def _character_build() -> CharacterBuild:
    return CharacterBuild(
        name="Magrat",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, WeaponType.FROST_STAFF),
        back_bar=_bar(BarId.BACK, WeaponType.RESTORATION_STAFF),
    )


def _saved_build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
        build.Armor[slot]["Weight"] = "Light"
    return build


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _completion() -> RotationHeavyAttackCompletionEvidence:
    return RotationHeavyAttackCompletionEvidence(
        action_time_seconds=6.0,
        action_sequence=0,
        completion_time_seconds=8.0,
        fully_charged=True,
        verified_base_restore=None,
        source="reviewed candidate heavy",
    )


class _ProgressionAdapter:
    def __init__(self, progression: CharacterProgression) -> None:
        self.progression = progression

    def resolve(self, _build):
        return SimpleNamespace(
            character_id="magrat",
            progression=self.progression,
            unresolved=(),
            resolved=True,
        )


class _ReplayService:
    def __init__(self) -> None:
        self.events = []

    def replay(self, *, restoration_resolver, plan, **_kwargs):
        heavy = next(
            action for action in plan.actions if action.kind is RotationActionKind.HEAVY_ATTACK
        )
        event = restoration_resolver(heavy)
        if event is not None:
            self.events.append(event)
        return SimpleNamespace(final_projection=SimpleNamespace(marker="post-heavy"))


class _ScorecardService:
    def __init__(self) -> None:
        self.calls = []

    def compare(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(label="candidate scorecard")


class _RankingService:
    def rank(self, candidates):
        return tuple(
            RotationCandidateRankingResult(
                candidate_id=item.candidate_id,
                scorecard=item.scorecard,
                tier=RotationCandidateTier.ELIGIBLE,
                rank=index + 1,
                reasons=("ranked with post-heavy sustain",),
            )
            for index, item in enumerate(candidates)
        )


def _ranking_service(progression: CharacterProgression, replay: _ReplayService, scorecards: _ScorecardService):
    heavy_service = RotationHeavySustainProjectionService(
        replay_service=replay,
        progression_adapter=_ProgressionAdapter(progression),
    )
    return RotationCandidateHeavySustainRankingService(
        heavy_service=heavy_service,
        scorecard_service=scorecards,
        ranking_service=_RankingService(),
    )


def test_candidate_ranking_uses_saved_cycle_of_life_restore_before_scoring() -> None:
    heavy = RotationAction(6.0, 0, RotationActionKind.HEAVY_ATTACK)
    candidate_plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        heavy,
    )
    replay = _ReplayService()
    scorecards = _ScorecardService()
    service = _ranking_service(
        CharacterProgression(passive_ranks={"Cycle of Life": 2}),
        replay,
        scorecards,
    )

    results = service.evaluate_and_rank(
        character_build=_character_build(),
        sustain_build=_saved_build(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        baseline_plan=_plan(),
        baseline_sustain=SimpleNamespace(marker="baseline"),
        candidates=(
            RotationCandidateHeavySustainInput(
                "resto-heavy",
                candidate_plan,
                (_completion(),),
            ),
        ),
    )

    assert results[0].tier is RotationCandidateTier.ELIGIBLE
    assert results[0].rank == 1
    assert len(replay.events) == 1
    assert replay.events[0].amount == pytest.approx(3267.0 * 1.30)
    assert scorecards.calls[0]["candidate_sustain"].marker == "post-heavy"


def test_unknown_cycle_of_life_blocks_candidate_before_scorecard_ranking() -> None:
    candidate_plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        RotationAction(6.0, 0, RotationActionKind.HEAVY_ATTACK),
    )
    replay = _ReplayService()
    scorecards = _ScorecardService()
    service = _ranking_service(
        CharacterProgression(passive_ranks={}),
        replay,
        scorecards,
    )

    result = service.evaluate_and_rank(
        character_build=_character_build(),
        sustain_build=_saved_build(),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        baseline_plan=_plan(),
        baseline_sustain=SimpleNamespace(marker="baseline"),
        candidates=(
            RotationCandidateHeavySustainInput(
                "unknown-cycle",
                candidate_plan,
                (_completion(),),
            ),
        ),
    )[0]

    assert result.tier is RotationCandidateTier.INELIGIBLE
    assert result.scorecard is None
    assert any("Cycle of Life rank is unknown" in reason for reason in result.reasons)
    assert replay.events == []
    assert scorecards.calls == []
