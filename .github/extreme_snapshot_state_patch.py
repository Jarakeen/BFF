from pathlib import Path

service_text = '''from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_runtime_buff_service import (
    ExtremeActualHealGearRuntimeBuffService,
)
from services.extreme_actual_heal_skill_buff_candidate_service import (
    ExtremeActualHealSkillBuffCandidateService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeRuntimeSnapshotCombatStateResult:
    combat_state: CombatState
    unresolved: tuple[str, ...] = ()


class ExtremeRuntimeSnapshotCombatStateService:
    """Project one role-neutral Extreme runtime snapshot into CombatState.

    This is the shared E1 projection boundary for role objectives. It reuses the
    existing named-buff skill and gear history resolvers and owns potion-window
    projection until potion use joins the same canonical runtime-event stream.
    Role-specific healing, tanking, or damage modifiers layer on top afterward.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_buff_candidates: ExtremeActualHealSkillBuffCandidateService | None = None,
        gear_runtime_buffs: ExtremeActualHealGearRuntimeBuffService | None = None,
        potion_use_resolver: PotionUseEventResolver | None = None,
    ) -> None:
        self.database_path = None if database_path is None else Path(database_path)
        self.skill_buff_candidates = skill_buff_candidates
        self.gear_runtime_buffs = gear_runtime_buffs
        self.potion_use_resolver = potion_use_resolver

    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        active_bar: str,
        snapshot: ExtremeRuntimeSnapshot,
        base_active_buffs: tuple[str, ...] = (),
    ) -> ExtremeRuntimeSnapshotCombatStateResult:
        active_buffs = [
            name
            for raw_name in base_active_buffs
            if (name := str(raw_name or "").strip())
        ]
        unresolved: list[str] = []
        in_combat = False

        if snapshot.attempts:
            skill_service = self.skill_buff_candidates
            if skill_service is None and self.database_path is not None:
                skill_service = ExtremeActualHealSkillBuffCandidateService(self.database_path)
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
            if gear_service is None and self.database_path is not None:
                gear_service = ExtremeActualHealGearRuntimeBuffService(self.database_path)
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

        if snapshot.potion_elapsed_seconds is not None:
            potion_name = " ".join(str(build.Potion or "").strip().split())
            if not potion_name:
                unresolved.append(
                    "Explicit potion-use window requested but build has no potion selection"
                )
            else:
                medicinal_use_rank = progression.passive_rank("Medicinal Use")
                if medicinal_use_rank is None:
                    unresolved.append(
                        "Medicinal Use rank is unresolved for explicit potion-use window"
                    )
                else:
                    resolver = self.potion_use_resolver
                    if resolver is None:
                        resolver = PotionUseEventResolver(database_path=self.database_path)
                        self.potion_use_resolver = resolver
                    event = resolver.resolve(potion_name)
                    unresolved.extend(event.unresolved)
                    if event.resolved:
                        try:
                            cadence = PotionCadence(
                                event, medicinal_use_rank=medicinal_use_rank
                            )
                        except ValueError as exc:
                            unresolved.append(str(exc))
                        else:
                            active_buffs.extend(
                                cadence.window(
                                    snapshot.potion_elapsed_seconds
                                ).active_buff_names
                            )

        return ExtremeRuntimeSnapshotCombatStateResult(
            combat_state=CombatState(
                in_combat=in_combat,
                active_buffs=tuple(dict.fromkeys(active_buffs)),
            ),
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
'''
Path('services/extreme_runtime_snapshot_combat_state_service.py').write_text(service_text)

path = Path('services/extreme_conditional_actual_heal_optimization_service.py')
text = path.read_text()
import_anchor = 'from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot\n'
new_import = '''from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
'''
if 'ExtremeRuntimeSnapshotCombatStateService' not in text:
    if import_anchor not in text:
        raise SystemExit('snapshot state import anchor missing')
    text = text.replace(import_anchor, new_import, 1)

arg_anchor = '''        gear_runtime_buffs: ExtremeActualHealGearRuntimeBuffService | None = None,
        restoration_heavy_state: ExtremeRestorationHeavyCombatStateService | None = None,
'''
if 'runtime_snapshot_state: ExtremeRuntimeSnapshotCombatStateService | None = None' not in text:
    if arg_anchor not in text:
        raise SystemExit('snapshot state argument anchor missing')
    text = text.replace(
        arg_anchor,
        '''        gear_runtime_buffs: ExtremeActualHealGearRuntimeBuffService | None = None,
        runtime_snapshot_state: ExtremeRuntimeSnapshotCombatStateService | None = None,
        restoration_heavy_state: ExtremeRestorationHeavyCombatStateService | None = None,
''',
        1,
    )

set_anchor = '''        self.gear_runtime_buffs = gear_runtime_buffs
        self.restoration_heavy_state = restoration_heavy_state
'''
if 'self.runtime_snapshot_state = runtime_snapshot_state' not in text:
    if set_anchor not in text:
        raise SystemExit('snapshot state assignment anchor missing')
    text = text.replace(
        set_anchor,
        '''        self.gear_runtime_buffs = gear_runtime_buffs
        self.runtime_snapshot_state = runtime_snapshot_state
        self.restoration_heavy_state = restoration_heavy_state
''',
        1,
    )

old_history = '''        if self.runtime_snapshot is not None and self.runtime_snapshot.attempts:
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
new_history = '''        if self.runtime_snapshot is not None:
            state_service = self.runtime_snapshot_state
            if state_service is None:
                state_service = ExtremeRuntimeSnapshotCombatStateService(
                    getattr(self.optimizer, "database_path", None),
                    skill_buff_candidates=self.skill_buff_candidates,
                    gear_runtime_buffs=self.gear_runtime_buffs,
                    potion_use_resolver=self.potion_use_resolver,
                )
                self.runtime_snapshot_state = state_service
            snapshot_result = state_service.resolve(
                build,
                progression=progression,
                active_bar=active_bar,
                snapshot=self.runtime_snapshot,
                base_active_buffs=tuple(active_buffs),
            )
            active_buffs = list(snapshot_result.combat_state.active_buffs)
            unresolved.extend(snapshot_result.unresolved)
            in_combat = in_combat or bool(snapshot_result.combat_state.in_combat)

'''
if new_history not in text:
    if old_history not in text:
        raise SystemExit('direct unified history block missing')
    text = text.replace(old_history, new_history, 1)

text = text.replace(
    '        if self.potion_elapsed_seconds is not None:\n            potion_name = " ".join(str(build.Potion or "").strip().split())\n',
    '        if self.potion_elapsed_seconds is not None and self.runtime_snapshot is None:\n            potion_name = " ".join(str(build.Potion or "").strip().split())\n',
    1,
)
path.write_text(text)

test_text = '''from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


class _SkillHistory:
    def __init__(self):
        self.calls = []

    def active_triggered_named_buffs_history(
        self, build, *, active_bar, attempts, snapshot_time_seconds
    ):
        self.calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return ("Major Sorcery", "Major Sorcery")


class _GearHistory:
    def __init__(self, *, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve_history(self, build, *, active_bar, attempts, snapshot_time_seconds):
        self.calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return SimpleNamespace(
            active_buffs=("Major Courage",), unresolved=self.unresolved
        )


class _PotionResolver:
    def resolve(self, selected_label):
        _ = selected_label
        return SimpleNamespace(
            resolved=True,
            unresolved=(),
            buff_grants=(SimpleNamespace(buff_name="Major Sorcery", duration=40.0),),
        )


def _attempt():
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=1.0,
            trigger="critical_heal",
            source="snapshot state test",
        )
    )


def test_snapshot_state_projects_skill_gear_and_potion_into_one_combat_state():
    attempts = (_attempt(),)
    skill = _SkillHistory()
    gear = _GearHistory()
    service = ExtremeRuntimeSnapshotCombatStateService(
        skill_buff_candidates=skill,
        gear_runtime_buffs=gear,
        potion_use_resolver=_PotionResolver(),
    )

    result = service.resolve(
        PlayerBuild(BuildName="Shared Snapshot", Potion="Increase Spell Power"),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            attempts=attempts,
            snapshot_time_seconds=5.0,
            potion_elapsed_seconds=5.0,
        ),
        base_active_buffs=("Minor Mending", "Major Sorcery"),
    )

    assert result.unresolved == ()
    assert result.combat_state.in_combat
    assert result.combat_state.active_buffs == (
        "Minor Mending",
        "Major Sorcery",
        "Major Courage",
    )
    assert skill.calls[0][2:] == (attempts, 5.0)
    assert gear.calls[0][2:] == (attempts, 5.0)


def test_snapshot_state_preserves_gear_runtime_blockers():
    service = ExtremeRuntimeSnapshotCombatStateService(
        skill_buff_candidates=_SkillHistory(),
        gear_runtime_buffs=_GearHistory(unresolved=("proc stacking unresolved",)),
    )
    result = service.resolve(
        PlayerBuild(BuildName="Blocked Snapshot"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            attempts=(_attempt(),), snapshot_time_seconds=5.0
        ),
    )
    assert result.unresolved == ("proc stacking unresolved",)


def test_snapshot_state_requires_medicinal_use_proof_for_potion_window():
    service = ExtremeRuntimeSnapshotCombatStateService(
        potion_use_resolver=_PotionResolver()
    )
    result = service.resolve(
        PlayerBuild(BuildName="Potion Proof", Potion="Increase Spell Power"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            snapshot_time_seconds=5.0, potion_elapsed_seconds=5.0
        ),
    )
    assert result.unresolved == (
        "Medicinal Use rank is unresolved for explicit potion-use window",
    )


def test_snapshot_state_without_runtime_sources_preserves_base_state():
    service = ExtremeRuntimeSnapshotCombatStateService()
    result = service.resolve(
        PlayerBuild(BuildName="Static Snapshot"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=0.0),
        base_active_buffs=("Major Sorcery", "Major Sorcery"),
    )
    assert not result.combat_state.in_combat
    assert result.combat_state.active_buffs == ("Major Sorcery",)
    assert result.unresolved == ()
'''
Path('services/tests/test_extreme_runtime_snapshot_combat_state_service.py').write_text(test_text)

notes = Path('GAME_MECHANICS_FIELD_NOTES.md')
content = notes.read_text()
heading = '## 2026-09-09 — Extreme runtime snapshots need one role-neutral CombatState projector'
if heading not in content:
    content += '''

---

## 2026-09-09 — Extreme runtime snapshots need one role-neutral CombatState projector

The unified `ExtremeRuntimeSnapshot` contract is projected through one shared `ExtremeRuntimeSnapshotCombatStateService` before a role objective evaluates its own healing, tanking, or damage semantics. The projector owns ordered skill-history named buffs, gear-proc history, and explicit potion-window activation, deduplicates the resulting named buffs, and preserves runtime blockers. Healer-specific states such as Restoration Staff heavy completion or Sacred Ground still layer afterward until those mechanics are represented as role-neutral canonical runtime evidence. Tank and Damage Dealer Extreme objectives should consume this projector rather than recreate runtime truth.
'''
    notes.write_text(content)
