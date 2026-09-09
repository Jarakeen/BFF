from pathlib import Path

snapshot_module = '''from __future__ import annotations

import math
from dataclasses import dataclass

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt


@dataclass(frozen=True)
class ExtremeRuntimeSnapshot:
    """One deterministic runtime history evaluated at one exact snapshot.

    The shared contract stays role-neutral. Ordered effect attempts carry
    their own chance and condition evidence; potion timing is retained here
    until potion use is represented by the same canonical runtime stream.
    """

    attempts: tuple[RuntimeEffectEventAttempt, ...] = ()
    snapshot_time_seconds: float = 0.0
    potion_elapsed_seconds: float | None = None

    def __post_init__(self) -> None:
        snapshot = float(self.snapshot_time_seconds)
        if not math.isfinite(snapshot) or snapshot < 0.0:
            raise ValueError("runtime snapshot time must be a finite non-negative number")
        object.__setattr__(self, "snapshot_time_seconds", snapshot)
        object.__setattr__(self, "attempts", tuple(self.attempts))
        if self.potion_elapsed_seconds is None:
            return
        potion_elapsed = float(self.potion_elapsed_seconds)
        if not math.isfinite(potion_elapsed) or potion_elapsed < 0.0:
            raise ValueError(
                "runtime snapshot potion elapsed time must be finite and non-negative"
            )
        object.__setattr__(self, "potion_elapsed_seconds", potion_elapsed)
'''
Path('services/extreme_runtime_snapshot.py').write_text(snapshot_module)

path = Path('services/extreme_conditional_actual_heal_optimization_service.py')
text = path.read_text()

import_anchor = '''from services.extreme_necromancer_living_death_healing_service import (
    ExtremeNecromancerLivingDeathHealingService,
)
'''
if 'from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot\n' not in text:
    if import_anchor not in text:
        raise SystemExit('runtime snapshot import anchor not found')
    text = text.replace(
        import_anchor,
        import_anchor + 'from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot\n',
        1,
    )

arg_anchor = '''        active_buffs: tuple[str, ...] = (),
        potion_elapsed_seconds: float | None = None,
'''
if 'runtime_snapshot: ExtremeRuntimeSnapshot | None = None' not in text:
    if arg_anchor not in text:
        raise SystemExit('runtime snapshot argument anchor not found')
    text = text.replace(
        arg_anchor,
        '''        active_buffs: tuple[str, ...] = (),
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        potion_elapsed_seconds: float | None = None,
''',
        1,
    )

potion_anchor = '''        if potion_elapsed_seconds is None:
            self.potion_elapsed_seconds = None
'''
if 'self.runtime_snapshot = runtime_snapshot' not in text:
    if potion_anchor not in text:
        raise SystemExit('runtime snapshot init anchor not found')
    runtime_init = '''        self.runtime_snapshot = runtime_snapshot
        if runtime_snapshot is not None:
            if any(
                value is not None
                for value in (
                    skill_trigger_event,
                    skill_trigger_snapshot_seconds,
                    gear_trigger_event,
                    gear_trigger_snapshot_seconds,
                )
            ):
                raise ValueError(
                    "runtime_snapshot cannot be combined with legacy skill/gear trigger inputs"
                )
            if potion_elapsed_seconds is not None:
                raise ValueError(
                    "runtime_snapshot potion timing must be supplied on the snapshot contract"
                )
            potion_elapsed_seconds = runtime_snapshot.potion_elapsed_seconds
'''
    text = text.replace(potion_anchor, runtime_init + potion_anchor, 1)

optimize_start = text.index('    def optimize(')
scenario_anchor = '''        if self.potion_elapsed_seconds is not None:
            scenarios.append(
'''
scenario_pos = text.index(scenario_anchor, optimize_start)
if 'unified runtime snapshot at ' not in text[optimize_start:scenario_pos]:
    unified_scenario = '''        if self.runtime_snapshot is not None:
            scenarios.append(
                "unified runtime snapshot at "
                f"{self.runtime_snapshot.snapshot_time_seconds:.6f}s from "
                f"{len(self.runtime_snapshot.attempts)} ordered event attempts"
            )
'''
    text = text[:scenario_pos] + unified_scenario + text[scenario_pos:]

additional_start = text.index('    def _additional_candidates(')
additional_return = text.index('        return tuple(result)', additional_start)
trigger_anchor = '        if self.skill_trigger_event is not None:\n'
trigger_pos = text.index(trigger_anchor, additional_start, additional_return)
if 'for attempt in self.runtime_snapshot.attempts' not in text[additional_start:trigger_pos]:
    candidate_block = '''        if self.runtime_snapshot is not None and self.runtime_snapshot.attempts:
            service = self.skill_buff_candidates
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = service
            if service is not None:
                for attempt in self.runtime_snapshot.attempts:
                    result.extend(
                        service.triggered_build_candidates(
                            baseline_build,
                            character_id=character_id,
                            baseline_build_id=baseline_build_id,
                            protected_entity_id=entity_id,
                            active_bar=active_bar,
                            event=attempt.event,
                            snapshot_time_seconds=self.runtime_snapshot.snapshot_time_seconds,
                            chance_roll=attempt.chance_roll,
                            condition_context=attempt.condition_context,
                        )
                    )
'''
    text = text[:trigger_pos] + candidate_block + text[trigger_pos:]

restoration_start = text.index('    def _restoration_combat_state(')
restoration_end = text.index('    def _templar_mending_event(', restoration_start)
trigger_pos = text.index(trigger_anchor, restoration_start, restoration_end)
if 'active_triggered_named_buffs_history' not in text[restoration_start:trigger_pos]:
    history_block = '''        if self.runtime_snapshot is not None and self.runtime_snapshot.attempts:
            snapshot = self.runtime_snapshot
            skill_service = self.skill_buff_candidates
            if skill_service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    skill_service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = skill_service
            if skill_service is not None:
                active_buffs.extend(
                    skill_service.active_triggered_named_buffs_history(
                        build,
                        active_bar=active_bar,
                        attempts=snapshot.attempts,
                        snapshot_time_seconds=snapshot.snapshot_time_seconds,
                    )
                )

            gear_service = self.gear_runtime_buffs
            if gear_service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    gear_service = ExtremeActualHealGearRuntimeBuffService(database_path)
                    self.gear_runtime_buffs = gear_service
            if gear_service is not None:
                gear_result = gear_service.resolve_history(
                    build,
                    active_bar=active_bar,
                    attempts=snapshot.attempts,
                    snapshot_time_seconds=snapshot.snapshot_time_seconds,
                )
                active_buffs.extend(gear_result.active_buffs)
                unresolved.extend(gear_result.unresolved)
            in_combat = True

'''
    text = text[:trigger_pos] + history_block + text[trigger_pos:]

path.write_text(text)

test_path = Path('services/tests/test_extreme_conditional_actual_heal_optimization_service.py')
tests = test_path.read_text()
if 'from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt\n' not in tests:
    tests = tests.replace(
        'from minmax.combat_state import CombatState\n',
        'from minmax.combat_state import CombatState\nfrom minmax.runtime_effect_sequence import RuntimeEffectEventAttempt\nfrom minmax.runtime_event import RuntimeEvent\n',
        1,
    )
if 'from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot\n' not in tests:
    tests = tests.replace(
        '''from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
''',
        '''from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
''',
        1,
    )

if 'def test_unified_runtime_snapshot_combines_skill_and_gear_history():' not in tests:
    tests += '''

class _HistorySkillBuffCandidates:
    def __init__(self):
        self.history_calls = []

    def active_triggered_named_buffs_history(
        self, build, *, active_bar, attempts, snapshot_time_seconds
    ):
        self.history_calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return ("Major Sorcery",)

    def triggered_build_candidates(self, *args, **kwargs):
        _ = args, kwargs
        return ()


class _HistoryGearRuntimeBuffs:
    def __init__(self):
        self.history_calls = []

    def resolve_history(self, build, *, active_bar, attempts, snapshot_time_seconds):
        self.history_calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return SimpleNamespace(active_buffs=("Major Courage",), unresolved=())


def _runtime_attempt(time_seconds=1.0, trigger="critical_heal"):
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=time_seconds,
            trigger=trigger,
            source="test runtime history",
        )
    )


def test_unified_runtime_snapshot_combines_skill_and_gear_history():
    attempts = (_runtime_attempt(1.0), _runtime_attempt(3.0, "overheal_self_or_ally"))
    skill = _HistorySkillBuffCandidates()
    gear = _HistoryGearRuntimeBuffs()
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        runtime_snapshot=ExtremeRuntimeSnapshot(
            attempts=attempts, snapshot_time_seconds=5.0
        ),
        skill_buff_candidates=skill,
        gear_runtime_buffs=gear,
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Unified Snapshot"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
    )

    assert unresolved == ()
    assert state.in_combat
    assert state.active_buffs == ("Major Sorcery", "Major Courage")
    assert skill.history_calls[0][2:] == (attempts, 5.0)
    assert gear.history_calls[0][2:] == (attempts, 5.0)


def test_unified_runtime_snapshot_routes_potion_timing_through_same_contract():
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        runtime_snapshot=ExtremeRuntimeSnapshot(
            snapshot_time_seconds=20.0, potion_elapsed_seconds=20.0
        ),
        potion_use_resolver=_PotionUseResolver(duration=40.0),
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(
            BuildName="Unified Potion Snapshot", Potion="Increase Spell Power"
        ),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        active_bar="front",
    )

    assert unresolved == ()
    assert state.has_buff("Major Sorcery")
    assert service.potion_elapsed_seconds == 20.0


def test_unified_runtime_snapshot_rejects_legacy_trigger_inputs():
    with pytest.raises(ValueError, match="cannot be combined with legacy skill/gear trigger inputs"):
        ExtremeConditionalActualHealOptimizationService(
            target_health_fraction=0.29,
            runtime_snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=5.0),
            skill_trigger_event=RuntimeEvent(
                time_seconds=1.0, trigger="critical_heal", source="legacy"
            ),
            skill_trigger_snapshot_seconds=5.0,
            optimizer=_Optimizer(),
            healing_events=_ConditionalHealingEvents(),
        )


def test_unified_runtime_snapshot_rejects_legacy_potion_timing():
    with pytest.raises(ValueError, match="potion timing must be supplied on the snapshot contract"):
        ExtremeConditionalActualHealOptimizationService(
            target_health_fraction=0.29,
            runtime_snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=5.0),
            potion_elapsed_seconds=1.0,
            optimizer=_Optimizer(),
            healing_events=_ConditionalHealingEvents(),
        )


def test_unified_runtime_snapshot_is_stamped_in_search_scope(monkeypatch):
    _install_progression_adapter(monkeypatch)
    service = ExtremeConditionalActualHealOptimizationService(
        target_health_fraction=0.29,
        runtime_snapshot=ExtremeRuntimeSnapshot(
            attempts=(_runtime_attempt(1.0),), snapshot_time_seconds=5.0
        ),
        skill_buff_candidates=_HistorySkillBuffCandidates(),
        gear_runtime_buffs=_HistoryGearRuntimeBuffs(),
        optimizer=_Optimizer(),
        healing_events=_ConditionalHealingEvents(),
    )

    result = service.optimize(
        PlayerBuild(BuildName="Unified Scope"),
        "blessing_of_protection",
        max_passes=1,
    )

    assert any(
        "unified runtime snapshot at 5.000000s from 1 ordered event attempts" in item
        for item in result.search_scope
    )


def test_unified_runtime_snapshot_validates_time_boundaries():
    with pytest.raises(ValueError, match="finite non-negative"):
        ExtremeRuntimeSnapshot(snapshot_time_seconds=-0.01)
    with pytest.raises(ValueError, match="potion elapsed time must be finite and non-negative"):
        ExtremeRuntimeSnapshot(snapshot_time_seconds=0.0, potion_elapsed_seconds=-0.01)
'''

test_path.write_text(tests)

notes = Path('GAME_MECHANICS_FIELD_NOTES.md')
notes_text = notes.read_text()
heading = '## 2026-09-09 — Extreme snapshot optimization needs one runtime-history contract'
if heading not in notes_text:
    notes_text += '''

---

## 2026-09-09 — Extreme snapshot optimization needs one runtime-history contract

Extreme role objectives should not maintain separate temporal truth for skill triggers, gear procs, and potion windows. The first unified runtime-snapshot contract carries one ordered `RuntimeEffectEventAttempt` history, one exact snapshot time, and potion elapsed timing while potion use remains outside the shared runtime stream. Skill and gear buffs are both resolved from that same ordered history before the candidate `CombatState` is built. Legacy single-trigger inputs remain supported only when the unified snapshot is absent; mixing the two paths is rejected to prevent double application. Class-specific emergency assumptions still layer into the same `CombatState` until their windows are represented by role-neutral canonical runtime evidence.
'''
    notes.write_text(notes_text)
