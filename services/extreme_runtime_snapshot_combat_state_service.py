from __future__ import annotations

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
