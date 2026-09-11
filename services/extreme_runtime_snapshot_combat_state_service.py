from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.external_group_buff_provenance import ExternalGroupBuffProvenanceResolver
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_runtime_buff_service import (
    ExtremeActualHealGearRuntimeBuffService,
)
from services.extreme_actual_heal_skill_buff_candidate_service import (
    ExtremeActualHealSkillBuffCandidateService,
)
from services.extreme_dual_bar_gear_runtime_legality_service import (
    ExtremeDualBarGearRuntimeLegalityService,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidenceCatalog,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeRuntimeSnapshotCombatStateResult:
    combat_state: CombatState
    unresolved: tuple[str, ...] = ()


class ExtremeRuntimeSnapshotCombatStateService:
    """Project one role-neutral runtime snapshot into CombatState.

    The class keeps its original Extreme-prefixed name for compatibility, but the
    responsibility is intentionally shared. Skill, gear, potion, and externally
    supplied group-buff runtime evidence enter through the snapshot's authoritative
    ordered runtime history. Role-specific healing, tanking, damage, rotation, or
    provider interpretation belongs above this projection boundary.

    When ``gear_activation`` is supplied, gear proc projection uses the full
    two-bar legality path and therefore requires bar provenance on runtime effect
    attempts. Without that evidence, the older active-snapshot gear path remains
    available for compatibility. The two paths are mutually exclusive for one
    projection so gear buffs cannot be double-counted.

    ``base_combat_state`` preserves explicit snapshot facts that the runtime history
    does not own, including game-update semantics and Emperor state. Runtime-proven
    named buffs are merged into that base state rather than replacing it. The older
    ``base_active_buffs`` parameter remains a compatibility view and is merged after
    the base state's own active buffs.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_buff_candidates: ExtremeActualHealSkillBuffCandidateService | None = None,
        gear_runtime_buffs: ExtremeActualHealGearRuntimeBuffService | None = None,
        dual_bar_gear_runtime: ExtremeDualBarGearRuntimeLegalityService | None = None,
        potion_use_resolver: PotionUseEventResolver | None = None,
        external_group_buffs: ExternalGroupBuffProvenanceResolver | None = None,
    ) -> None:
        self.database_path = None if database_path is None else Path(database_path)
        self.skill_buff_candidates = skill_buff_candidates
        self.gear_runtime_buffs = gear_runtime_buffs
        self.dual_bar_gear_runtime = dual_bar_gear_runtime
        self.potion_use_resolver = potion_use_resolver
        self.external_group_buffs = external_group_buffs or ExternalGroupBuffProvenanceResolver()

    def _dual_bar_gear_service(self) -> ExtremeDualBarGearRuntimeLegalityService | None:
        if self.dual_bar_gear_runtime is not None:
            return self.dual_bar_gear_runtime
        if self.database_path is None:
            return None
        repository = GearSetRepository(self.database_path)
        self.dual_bar_gear_runtime = ExtremeDualBarGearRuntimeLegalityService(
            resolver=GearSetEffectVariantResolver(repository)
        )
        return self.dual_bar_gear_runtime

    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        active_bar: str,
        snapshot: ExtremeRuntimeSnapshot,
        gear_activation: ExtremeDualBarSetActivationEvidenceCatalog | None = None,
        base_combat_state: CombatState | None = None,
        base_active_buffs: tuple[str, ...] = (),
    ) -> ExtremeRuntimeSnapshotCombatStateResult:
        base_state = base_combat_state or CombatState()
        active_buffs = list(base_state.active_buffs)
        active_buffs.extend(
            name
            for raw_name in base_active_buffs
            if (name := str(raw_name or "").strip())
        )
        unresolved: list[str] = []
        in_combat = bool(base_state.in_combat)
        attempts = snapshot.effect_attempts

        if attempts:
            skill_service = self.skill_buff_candidates
            if skill_service is None and self.database_path is not None:
                skill_service = ExtremeActualHealSkillBuffCandidateService(self.database_path)
                self.skill_buff_candidates = skill_service
            if skill_service is not None:
                active_buffs.extend(
                    skill_service.active_triggered_named_buffs_history(
                        build,
                        active_bar=active_bar,
                        attempts=attempts,
                        snapshot_time_seconds=snapshot.snapshot_time_seconds,
                    )
                )

            if gear_activation is not None:
                if snapshot.unbarred_effect_attempts:
                    unresolved.append(
                        "Dual-bar gear runtime projection requires active-bar provenance for every effect attempt"
                    )
                gear_service = self._dual_bar_gear_service()
                if gear_service is None:
                    unresolved.append(
                        "Dual-bar gear runtime activation evidence was supplied but no gear runtime legality service is available"
                    )
                elif snapshot.bar_effect_attempts:
                    gear_result = gear_service.resolve_history(
                        gear_activation,
                        attempts=snapshot.bar_effect_attempts,
                        snapshot_time_seconds=snapshot.snapshot_time_seconds,
                    )
                    active_buffs.extend(gear_result.active_buffs)
                    unresolved.extend(gear_result.unresolved)
            else:
                gear_service = self.gear_runtime_buffs
                if gear_service is None and self.database_path is not None:
                    gear_service = ExtremeActualHealGearRuntimeBuffService(self.database_path)
                    self.gear_runtime_buffs = gear_service
                if gear_service is not None:
                    gear_result = gear_service.resolve_history(
                        build,
                        active_bar=active_bar,
                        attempts=attempts,
                        snapshot_time_seconds=snapshot.snapshot_time_seconds,
                    )
                    active_buffs.extend(gear_result.active_buffs)
                    unresolved.extend(gear_result.unresolved)
            in_combat = True

        potion_elapsed_seconds = snapshot.effective_potion_elapsed_seconds
        if potion_elapsed_seconds is not None:
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
                                    potion_elapsed_seconds
                                ).active_buff_names
                            )

        external_applications = snapshot.external_group_buff_applications
        if external_applications:
            if snapshot.recipient_actor_id is None:
                unresolved.append(
                    "External group buff applications require a proven recipient actor id"
                )
            elif not snapshot.group_member_ids:
                unresolved.append(
                    "External group buff applications require proven group membership"
                )
            else:
                projection = self.external_group_buffs.resolve(
                    recipient_actor_id=snapshot.recipient_actor_id,
                    group_member_ids=snapshot.group_member_ids,
                    snapshot_time_seconds=snapshot.snapshot_time_seconds,
                    applications=external_applications,
                )
                active_buffs.extend(projection.active_buffs)
                unresolved.extend(projection.unresolved)

        return ExtremeRuntimeSnapshotCombatStateResult(
            combat_state=CombatState(
                in_combat=in_combat,
                active_buffs=tuple(dict.fromkeys(active_buffs)),
                game_update=base_state.game_update,
                is_emperor=base_state.is_emperor,
                in_home_campaign=base_state.in_home_campaign,
                emperor_home_keeps=base_state.emperor_home_keeps,
            ),
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
