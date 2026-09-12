from __future__ import annotations

from pathlib import Path

from engine.config import get_data_dir
from minmax.combat_state import CombatState
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateService,
)
from services.rotation_runtime_activation_anchor_evidence_service import (
    RotationRuntimeActivationAnchorEvidence,
    RotationRuntimeActivationAnchorEvidenceService,
)
from ui.rotation_canonical_candidate_support import (
    RotationCanonicalCandidateApplicationResult,
    RotationCanonicalCandidateSupport,
)
from ui.rotation_recovery_validation_support import (
    RotationRecoveryValidationEvidence,
    RotationRecoveryValidationScope,
)


class RotationRuntimeSnapshotCandidateSupport:
    """Project canonical runtime evidence before rotation candidate evaluation.

    The existing role-neutral runtime-snapshot projector remains authoritative even
    though its compatibility class name is still Extreme-prefixed. This adapter owns
    no proc, potion, named-buff, or external-group-buff mechanics. It only resolves
    that shared runtime evidence into ``CombatState`` and forwards the result into
    the already-decorated Rotation candidate path.

    ``canonical_candidates`` is the execution chain after weapon, target, potion,
    Ultimate, or other candidate decorators have been installed. ``base_canonical``
    is the underlying canonical candidate bridge that owns saved-build adaptation and
    static progression evidence. Keeping those references explicit avoids making a
    decorator pretend it owns canonical build identity.

    ``runtime_snapshot_active_bar`` remains deliberately explicit for the supplied
    one-instant snapshot. A snapshot may occur after any number of bar swaps, and the
    seed schedule is not authoritative for a later stabilized candidate. When the
    snapshot also carries unified ``runtime_history``, this adapter separately binds
    a final-plan resolver that derives active bar from each stabilized plan at the
    exact queried time/sequence.

    Explicit runtime activation-anchor evidence is independent caller-owned evidence.
    It is converted to a final-plan resolver factory without inferring impact timing
    from generic RuntimeEvent source text or numeric ESO IDs. If an evidence row no
    longer matches the stabilized action identity, downstream periodic projection
    remains fail-closed.

    Explicit ``combat_state`` remains useful as base snapshot context for facts not
    owned by runtime history, including game-update and Emperor state. Runtime-proven
    buffs are merged into that base state by the shared projector.
    """

    def __init__(
        self,
        *,
        canonical_candidates,
        base_canonical: RotationCanonicalCandidateSupport | None = None,
        database_path: str | Path | None = None,
        runtime_snapshot_state: ExtremeRuntimeSnapshotCombatStateService | None = None,
        plan_runtime_state: RotationPlanRuntimeCombatStateService | None = None,
        activation_anchor_evidence_service: RotationRuntimeActivationAnchorEvidenceService | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.canonical_candidates = canonical_candidates
        self.base_canonical = base_canonical or canonical_candidates
        if not isinstance(self.base_canonical, RotationCanonicalCandidateSupport):
            raise TypeError(
                "rotation runtime snapshot support requires an explicit "
                "RotationCanonicalCandidateSupport evidence owner"
            )
        self.runtime_snapshot_state = (
            runtime_snapshot_state
            or ExtremeRuntimeSnapshotCombatStateService(database)
        )
        self.plan_runtime_state = plan_runtime_state or RotationPlanRuntimeCombatStateService(
            runtime_snapshot_state=self.runtime_snapshot_state,
        )
        self.activation_anchor_evidence_service = (
            activation_anchor_evidence_service
            or RotationRuntimeActivationAnchorEvidenceService()
        )

    @property
    def static_context_service(self):
        return self.base_canonical.static_context_service

    @property
    def build_adapter(self):
        return self.base_canonical.build_adapter

    def run_effects(
        self,
        *,
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        runtime_snapshot_active_bar: str | None = None,
        runtime_activation_anchor_evidence: tuple[
            RotationRuntimeActivationAnchorEvidence, ...
        ] = (),
        **kwargs,
    ):
        anchor_evidence = tuple(runtime_activation_anchor_evidence)
        if (
            anchor_evidence
            and kwargs.get("runtime_activation_anchor_resolver_factory") is not None
        ):
            raise ValueError(
                "runtime activation-anchor evidence cannot be combined with an explicit "
                "runtime_activation_anchor_resolver_factory"
            )

        if runtime_snapshot is None:
            forwarded = dict(kwargs)
            if anchor_evidence:
                forwarded["runtime_activation_anchor_resolver_factory"] = (
                    self.activation_anchor_evidence_service.resolver_factory(
                        anchor_evidence
                    )
                )
            return self.canonical_candidates.run_effects(**forwarded)

        player_build = kwargs["player_build"]
        character_id = kwargs.get("character_id")
        active_bar = str(runtime_snapshot_active_bar or "").strip().casefold()
        if active_bar not in {"front", "back"}:
            return self._blocked_result(
                player_build=player_build,
                character_id=character_id,
                reason=(
                    "runtime snapshot rotation evaluation requires explicit "
                    "runtime_snapshot_active_bar evidence (front or back)"
                ),
            )

        static_service = self.static_context_service
        if static_service is None:
            return self._blocked_result(
                player_build=player_build,
                character_id=character_id,
                reason=(
                    "runtime snapshot rotation evaluation requires the canonical "
                    "static build context service"
                ),
            )

        progression = static_service.progression_adapter.resolve(player_build)
        if not progression.resolved:
            # The canonical candidate path already owns the normal progression
            # failure explanation. Delegate so there is only one user-facing truth.
            return self.canonical_candidates.run_effects(**kwargs)

        base_state = kwargs.get("combat_state")
        if base_state is None:
            base_state = CombatState()

        runtime_state = self.runtime_snapshot_state.resolve(
            player_build,
            progression=progression.progression,
            active_bar=active_bar,
            snapshot=runtime_snapshot,
            base_combat_state=base_state,
        )
        if runtime_state.unresolved:
            return self._blocked_result(
                player_build=player_build,
                character_id=character_id,
                reason=(
                    "runtime snapshot rotation evaluation is unresolved: "
                    + "; ".join(runtime_state.unresolved)
                ),
            )

        forwarded = dict(kwargs)
        forwarded["combat_state"] = runtime_state.combat_state
        if anchor_evidence:
            forwarded["runtime_activation_anchor_resolver_factory"] = (
                self.activation_anchor_evidence_service.resolver_factory(
                    anchor_evidence
                )
            )
        if runtime_snapshot.runtime_history:
            initial_bar = str(kwargs.get("initial_bar", "front") or "front")

            def runtime_combat_state_resolver_factory(plan):
                def resolve(time_seconds: float, sequence: int | None = None):
                    return self.plan_runtime_state.resolve(
                        player_build,
                        progression=progression.progression,
                        plan=plan,
                        runtime_snapshot_source=runtime_snapshot,
                        time_seconds=time_seconds,
                        sequence=sequence,
                        initial_bar=initial_bar,
                        base_combat_state=base_state,
                    )

                return resolve

            forwarded["runtime_combat_state_resolver_factory"] = (
                runtime_combat_state_resolver_factory
            )
        return self.canonical_candidates.run_effects(**forwarded)

    def _blocked_result(
        self,
        *,
        player_build,
        character_id: str | None,
        reason: str,
    ) -> RotationCanonicalCandidateApplicationResult:
        adaptation = self.build_adapter.adapt(
            player_build,
            character_id=character_id,
        )
        reasons = [reason]
        reasons.extend(
            f"saved-build adaptation: {item}"
            for item in adaptation.unresolved
            if str(item).strip()
        )
        if adaptation.build is None and not adaptation.unresolved:
            reasons.append("saved-build adaptation returned no canonical CharacterBuild")
        return RotationCanonicalCandidateApplicationResult(
            build_adaptation=adaptation,
            pipeline_result=None,
            validation=RotationRecoveryValidationEvidence(
                scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                selectable=None,
                reasons=tuple(reasons),
            ),
        )


__all__ = ["RotationRuntimeSnapshotCandidateSupport"]
