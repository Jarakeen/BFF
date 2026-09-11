from __future__ import annotations

from dataclasses import dataclass

from engine.config import DEFAULT_DATABASE
from minmax.character_build.character_build import CharacterBuild
from minmax.heavy_attack_restoration import HeavyAttackRestorationModifiers
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationPlan
from models.build_model import PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.heavy_attack_progression_modifier_service import (
    HeavyAttackProgressionModifierService,
)
from services.minmax_character_progression_adapter import (
    MinmaxCharacterProgressionAdapter,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
    RotationHeavyAttackResolvedModifiers,
    RotationHeavyAttackRestorationEvidenceService,
    RotationHeavyAttackRestorationProjection,
)
from services.rotation_recovery_heavy_replay_service import (
    RotationRecoveryHeavyReplay,
    RotationRecoveryHeavyReplayService,
)


@dataclass(frozen=True)
class RotationHeavySustainProjection:
    """Pre-scorecard sustain evidence after verified heavy restoration replay.

    A resolved projection is safe to hand to RotationCandidateScorecardService as
    `candidate_sustain`. Unresolved heavy completion/weapon/modifier evidence never
    becomes a zero-value restore or a silently ignored mechanic.
    """

    restoration_projection: RotationHeavyAttackRestorationProjection
    replay: RotationRecoveryHeavyReplay | None
    unresolved: tuple[str, ...]

    @property
    def is_resolved(self) -> bool:
        return self.replay is not None and not self.unresolved

    @property
    def sustain_projection(self):
        """Final replayed sustain projection, when heavy evidence is complete."""
        return None if self.replay is None else self.replay.final_projection


class RotationHeavySustainProjectionService:
    """Replay build-aware heavy restores before scorecard hard obligations run.

    Ordering matters. Resource shortfall and reserve requirements are hard candidate
    obligations, so verified heavy restoration must alter the resource timeline
    before those obligations are assessed. Applying heavy restoration after ranking
    would make an otherwise valid candidate impossible to recover from an artificial
    pre-heavy shortfall.

    Heavy weapon identity comes from CharacterBuild. Runtime cost/sustain evaluation
    uses the saved PlayerBuild bridge. Character-owned Cycle of Life and Revitalize
    are resolved from canonical progression and equipped armor before the restoration
    event is created. Explicit caller modifier evidence remains a reviewed override:
    it may fill an unknown progression value or agree with a known value, but a
    contradictory known character fact fails closed instead of double-applying.
    """

    _EPSILON = 1e-9

    def __init__(
        self,
        *,
        restoration_service: RotationHeavyAttackRestorationEvidenceService | None = None,
        replay_service: RotationRecoveryHeavyReplayService | None = None,
        progression_adapter: MinmaxCharacterProgressionAdapter | None = None,
        progression_modifier_service: HeavyAttackProgressionModifierService | None = None,
    ) -> None:
        self.restoration_service = (
            restoration_service or RotationHeavyAttackRestorationEvidenceService()
        )
        self.replay_service = replay_service or RotationRecoveryHeavyReplayService()
        inherited_adapter = getattr(
            getattr(self.replay_service, "sustain_service", None),
            "progression_adapter",
            None,
        )
        self.progression_adapter = progression_adapter or inherited_adapter or (
            MinmaxCharacterProgressionAdapter(
                BuildCatalogService(DEFAULT_DATABASE.with_name("characters.json"))
            )
        )
        self.progression_modifier_service = (
            progression_modifier_service or HeavyAttackProgressionModifierService()
        )

    def project(
        self,
        *,
        character_build: CharacterBuild,
        sustain_build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
    ) -> RotationHeavySustainProjection:
        progression_resolution = self.progression_adapter.resolve(sustain_build)
        progression = progression_resolution.progression

        def resolve_modifiers(action, weapon, evidence):
            progression_modifiers = self.progression_modifier_service.resolve(
                build=sustain_build,
                progression=progression,
                weapon=weapon,
            )
            return self._compose_modifiers(
                evidence=evidence,
                progression_resolution=progression_modifiers,
            )

        restoration = self.restoration_service.project(
            build=character_build,
            plan=plan,
            initial_bar=initial_bar,
            completion_evidence=tuple(completion_evidence),
            modifier_resolver=resolve_modifiers,
        )

        unresolved = list(restoration.unresolved)
        unresolved.extend(
            f"heavy-attack weapon projection violation at "
            f"{item.action.time_seconds:.3f}s sequence {item.action.sequence}: {item.reason}"
            for item in restoration.weapon_projection.violations
        )
        if unresolved:
            return RotationHeavySustainProjection(
                restoration_projection=restoration,
                replay=None,
                unresolved=self._dedupe(tuple(unresolved)),
            )

        event_by_action = {
            (float(item.action.time_seconds), int(item.action.sequence)): item.restoration_event
            for item in restoration.resolutions
            if item.restoration_event is not None
            and item.restoration_event.resource is resource
        }

        def resolve(action: RotationAction):
            return event_by_action.get((float(action.time_seconds), int(action.sequence)))

        replay = self.replay_service.replay(
            build=sustain_build,
            plan=plan,
            resource=resource,
            restoration_resolver=resolve,
        )
        return RotationHeavySustainProjection(
            restoration_projection=restoration,
            replay=replay,
            unresolved=(),
        )

    @classmethod
    def _compose_modifiers(
        cls,
        *,
        evidence: RotationHeavyAttackCompletionEvidence,
        progression_resolution,
    ) -> RotationHeavyAttackResolvedModifiers:
        explicit = evidence.modifiers
        canonical = progression_resolution.modifiers
        unresolved = list(progression_resolution.unresolved)

        cycle = canonical.restoration_staff_cycle_of_life_percent
        cycle_unknown = any(
            "Cycle of Life rank is unknown" in detail for detail in unresolved
        )
        if cycle_unknown and explicit.restoration_staff_cycle_of_life_percent > 0.0:
            unresolved = [
                detail
                for detail in unresolved
                if "Cycle of Life rank is unknown" not in detail
            ]
            cycle = explicit.restoration_staff_cycle_of_life_percent
        elif (
            progression_resolution.cycle_of_life_rank is not None
            and explicit.restoration_staff_cycle_of_life_percent > 0.0
            and abs(
                explicit.restoration_staff_cycle_of_life_percent - cycle
            ) > cls._EPSILON
        ):
            unresolved.append(
                "caller Cycle of Life modifier contradicts canonical character progression"
            )

        revitalize = canonical.heavy_armor_revitalize_percent
        revitalize_unknown = any(
            "Revitalize rank is unknown" in detail for detail in unresolved
        )
        if revitalize_unknown and explicit.heavy_armor_revitalize_percent > 0.0:
            unresolved = [
                detail
                for detail in unresolved
                if "Revitalize rank is unknown" not in detail
            ]
            revitalize = explicit.heavy_armor_revitalize_percent
        elif (
            progression_resolution.revitalize_rank is not None
            and explicit.heavy_armor_revitalize_percent > 0.0
            and abs(explicit.heavy_armor_revitalize_percent - revitalize) > cls._EPSILON
        ):
            unresolved.append(
                "caller Revitalize modifier contradicts canonical character progression"
            )

        return RotationHeavyAttackResolvedModifiers(
            modifiers=HeavyAttackRestorationModifiers(
                champion_point_percent=explicit.champion_point_percent,
                skill_set_buff_percent=explicit.skill_set_buff_percent,
                restoration_staff_cycle_of_life_percent=cycle,
                heavy_armor_revitalize_percent=revitalize,
            ),
            unresolved=cls._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationHeavySustainProjection",
    "RotationHeavySustainProjectionService",
]
