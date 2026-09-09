from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_target_type import SupportTargetType
from minmax.support_stacking import StackingBehavior
from models.build_model import PlayerBuild
from services.extreme_actual_heal_skill_buff_candidate_service import (
    ExtremeActualHealSkillBuffCandidateService,
)


class _Repository:
    @staticmethod
    def available_skills(character_class=None):
        _ = character_class
        return (
            (1, "Power Surge"),
            (2, "Conditional Power"),
            (3, "Ally Power"),
        )

    @staticmethod
    def resolve(ability_id):
        if ability_id == 1:
            return (
                EffectVariant(
                    name="major_sorcery",
                    layer=EffectLayer.CAST,
                    source="Power Surge",
                    duration=20.0,
                    target_type=SupportTargetType.SELF,
                ),
            )
        if ability_id == 2:
            return (
                EffectVariant(
                    name="major_sorcery",
                    layer=EffectLayer.CAST,
                    source="Conditional Power",
                    duration=20.0,
                    condition="while special condition is true",
                    target_type=SupportTargetType.SELF,
                ),
            )
        return (
            EffectVariant(
                name="major_sorcery",
                layer=EffectLayer.CAST,
                source="Ally Power",
                duration=20.0,
                target_type=SupportTargetType.ALLY,
            ),
        )


def _build():
    return PlayerBuild(
        BuildName="Skill Buff Search",
        EsoClass="Sorcerer",
        FrontBarSkills=[
            "Blessing of Protection",
            "Filler One",
            "Filler Two",
            "",
            "",
            "",
        ],
    )


def test_skill_buff_candidates_only_use_unconditional_self_named_buffs():
    service = ExtremeActualHealSkillBuffCandidateService(
        "unused.db", repository=_Repository()
    )
    candidates = service.build_candidates(
        _build(),
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="blessing_of_protection",
        active_bar="front",
    )

    assert candidates
    assert {candidate.changes[0].after["skill"] for candidate in candidates} == {"Power Surge"}
    assert all(candidate.changes[0].path != "FrontBarSkills[0]" for candidate in candidates)


def test_skill_buff_active_window_respects_exact_duration_boundary():
    service = ExtremeActualHealSkillBuffCandidateService(
        "unused.db", repository=_Repository()
    )
    build = _build()
    build.FrontBarSkills[1] = "Power Surge"

    assert service.active_named_buffs(
        build, active_bar="front", elapsed_seconds=19.999
    ) == ("Major Sorcery",)
    assert service.active_named_buffs(
        build, active_bar="front", elapsed_seconds=20.0
    ) == ()


def test_skill_buff_candidates_fail_closed_when_scored_heal_is_not_on_bar():
    service = ExtremeActualHealSkillBuffCandidateService(
        "unused.db", repository=_Repository()
    )
    assert service.build_candidates(
        _build(),
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="different_heal",
        active_bar="front",
    ) == ()


def test_triggered_skill_buff_requires_matching_runtime_trigger_and_duration():
    from minmax.runtime_event import RuntimeEvent

    class TriggeredRepository(_Repository):
        @staticmethod
        def available_skills(character_class=None):
            _ = character_class
            return ((4, "Triggered Power"),)

        @staticmethod
        def resolve(ability_id):
            assert ability_id == 4
            return (
                EffectVariant(
                    name="major_sorcery",
                    layer=EffectLayer.CAST,
                    source="Triggered Power",
                    duration=10.0,
                    trigger="critical_heal",
                    target_type=SupportTargetType.SELF,
                ),
            )

    service = ExtremeActualHealSkillBuffCandidateService(
        "unused.db", repository=TriggeredRepository()
    )
    build = _build()
    event = RuntimeEvent(time_seconds=5.0, trigger="critical_heal", source="test")

    candidates = service.triggered_build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="blessing_of_protection",
        active_bar="front",
        event=event,
        snapshot_time_seconds=14.999,
    )
    assert candidates
    assert {candidate.changes[0].after["skill"] for candidate in candidates} == {"Triggered Power"}

    assert service.triggered_build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="blessing_of_protection",
        active_bar="front",
        event=event,
        snapshot_time_seconds=15.0,
    ) == ()

    mismatch = RuntimeEvent(time_seconds=5.0, trigger="other_trigger", source="test")
    assert service.triggered_build_candidates(
        build,
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="blessing_of_protection",
        active_bar="front",
        event=mismatch,
        snapshot_time_seconds=6.0,
    ) == ()


def test_triggered_skill_buff_respects_explicit_proc_chance_roll():
    from minmax.runtime_event import RuntimeEvent

    class ChanceRepository(_Repository):
        @staticmethod
        def available_skills(character_class=None):
            _ = character_class
            return ((5, "Chance Power"),)

        @staticmethod
        def resolve(ability_id):
            assert ability_id == 5
            return (
                EffectVariant(
                    name="major_sorcery",
                    layer=EffectLayer.CAST,
                    source="Chance Power",
                    duration=10.0,
                    trigger="critical_heal",
                    chance=0.5,
                    target_type=SupportTargetType.SELF,
                ),
            )

    service = ExtremeActualHealSkillBuffCandidateService(
        "unused.db", repository=ChanceRepository()
    )
    build = _build()
    event = RuntimeEvent(time_seconds=0.0, trigger="critical_heal", source="test")
    kwargs = dict(
        baseline_build=build,
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="blessing_of_protection",
        active_bar="front",
        event=event,
        snapshot_time_seconds=1.0,
    )
    assert service.triggered_build_candidates(**kwargs) == ()
    assert service.triggered_build_candidates(**kwargs, chance_roll=0.49)
    assert service.triggered_build_candidates(**kwargs, chance_roll=0.50) == ()


def test_triggered_skill_buff_condition_requires_explicit_matching_context():
    from minmax.runtime_event import RuntimeEvent

    class ConditionalTriggeredRepository(_Repository):
        @staticmethod
        def available_skills(character_class=None):
            _ = character_class
            return ((6, "Conditional Triggered Power"),)

        @staticmethod
        def resolve(ability_id):
            assert ability_id == 6
            return (
                EffectVariant(
                    name="major_sorcery",
                    layer=EffectLayer.CAST,
                    source="Conditional Triggered Power",
                    duration=10.0,
                    trigger="critical_heal",
                    condition="target_below_half_health",
                    target_type=SupportTargetType.SELF,
                ),
            )

    service = ExtremeActualHealSkillBuffCandidateService(
        "unused.db", repository=ConditionalTriggeredRepository()
    )
    kwargs = dict(
        baseline_build=_build(),
        character_id="char-1",
        baseline_build_id="build-1",
        protected_entity_id="blessing_of_protection",
        active_bar="front",
        event=RuntimeEvent(time_seconds=0.0, trigger="critical_heal", source="test"),
        snapshot_time_seconds=1.0,
    )
    assert service.triggered_build_candidates(**kwargs) == ()
    assert service.triggered_build_candidates(
        **kwargs, condition_context=frozenset()
    ) == ()
    assert service.triggered_build_candidates(
        **kwargs, condition_context=frozenset({"target_below_half_health"})
    )


def test_triggered_skill_history_uses_latest_surviving_window():
    from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
    from minmax.runtime_event import RuntimeEvent
    class HistoryRepository(_Repository):
        @staticmethod
        def available_skills(character_class=None):
            return ((7, "History Power"),)
        @staticmethod
        def resolve(ability_id):
            return (EffectVariant(name="major_sorcery", layer=EffectLayer.CAST, source="History Power", duration=10.0, trigger="critical_heal", target_type=SupportTargetType.SELF, stacking=StackingBehavior.UNIQUE),)
    service = ExtremeActualHealSkillBuffCandidateService("unused.db", repository=HistoryRepository())
    build = _build()
    build.FrontBarSkills[1] = "History Power"
    attempts = (
        RuntimeEffectEventAttempt(RuntimeEvent(time_seconds=0.0, trigger="critical_heal", source="first")),
        RuntimeEffectEventAttempt(RuntimeEvent(time_seconds=11.0, trigger="critical_heal", source="second")),
    )
    assert service.active_triggered_named_buffs_history(build, active_bar="front", attempts=attempts, snapshot_time_seconds=15.0) == ("Major Sorcery",)
    assert service.active_triggered_named_buffs_history(build, active_bar="front", attempts=attempts, snapshot_time_seconds=21.0) == ()
