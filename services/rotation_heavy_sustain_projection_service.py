from __future__ import annotations

from dataclasses import dataclass
import re

from engine.config import DEFAULT_DATABASE
from minmax.character_build.character_build import CharacterBuild
from minmax.heavy_attack_restoration import HeavyAttackRestorationModifiers
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
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
    VerifiedRecoveryHeavyRestorationResolver,
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

    The same canonical restoration projection may also be exposed as a plan-specific
    replay resolver. Recovery-heavy stabilization can therefore rebuild restoration
    evidence for each regenerated plan without replaying sustain twice or creating a
    second Heavy Attack math path.

    Duration-aware recovery generation currently records a verified Heavy Attack
    reservation in the plan's provenance text. BFF's reviewed gameplay scheduling
    window for a fully charged heavy is 1.8 seconds. Only an exact heavy reservation
    matching that reviewed window is promoted to completion evidence here; merely
    seeing a HEAVY_ATTACK action in a plan is never enough.
    """

    _EPSILON = 1e-9
    _REVIEWED_FULLY_CHARGED_HEAVY_WINDOW_SECONDS = 1.8
    _RESERVED_HEAVY_PATTERN = re.compile(
        r"^caller-proven heavy_attack at "
        r"(?P<start>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)s reserved "
        r"the (?P<bar>front|back)-bar timeline through "
        r"(?P<end>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)s$"
    )

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

    @classmethod
    def completion_evidence_from_verified_reservations(
        cls,
        plan: RotationPlan,
    ) -> tuple[RotationHeavyAttackCompletionEvidence, ...]:
        """Promote reviewed 1.8s scheduler reservations to full-charge evidence.

        The duration-aware scheduler records reservation provenance only after the
        caller-proven decision passed channel-boundary validation. This adapter is
        deliberately narrow: the reservation must name ``heavy_attack``, match one
        scheduled heavy on the same bar and start timestamp, and reserve exactly the
        reviewed 1.8-second full-charge gameplay window. Any other duration remains
        unpromoted so older/reference animation timings cannot silently redefine the
        Rotation Builder's reviewed completion boundary.
        """

        heavies = tuple(
            action
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )
        evidence: list[RotationHeavyAttackCompletionEvidence] = []
        seen: set[tuple[float, int]] = set()

        for raw in plan.unresolved:
            match = cls._RESERVED_HEAVY_PATTERN.fullmatch(str(raw).strip())
            if match is None:
                continue
            start = float(match.group("start"))
            end = float(match.group("end"))
            bar = match.group("bar")
            reservation = end - start
            if abs(
                reservation - cls._REVIEWED_FULLY_CHARGED_HEAVY_WINDOW_SECONDS
            ) > cls._EPSILON:
                continue

            matching = tuple(
                action
                for action in heavies
                if abs(float(action.time_seconds) - start) <= cls._EPSILON
                and action.bar == bar
            )
            if len(matching) != 1:
                continue
            action = matching[0]
            key = (float(action.time_seconds), int(action.sequence))
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                RotationHeavyAttackCompletionEvidence(
                    action_time_seconds=action.time_seconds,
                    action_sequence=action.sequence,
                    completion_time_seconds=end,
                    fully_charged=True,
                    verified_base_restore=None,
                    source=(
                        "duration-aware verified 1.8s heavy-attack channel reservation"
                    ),
                )
            )

        return tuple(
            sorted(
                evidence,
                key=lambda item: (
                    item.action_time_seconds,
                    item.action_sequence,
                ),
            )
        )

    def restoration_resolver_for_plan(
        self,
        *,
        character_build: CharacterBuild,
        sustain_build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
    ) -> VerifiedRecoveryHeavyRestorationResolver:
        """Build a canonical replay resolver for one exact generated plan.

        This method performs weapon/bar resolution, canonical saved-character passive
        resolution, reviewed modifier composition, and verified base-restore math,
        but deliberately does not replay sustain. Any unresolved restoration evidence
        raises before replay so a recovery-heavy caller cannot silently convert an
        unknown restore into zero.
        """

        restoration = self._restoration_projection(
            character_build=character_build,
            sustain_build=sustain_build,
            plan=plan,
            initial_bar=initial_bar,
            completion_evidence=completion_evidence,
        )
        unresolved = self._restoration_unresolved(restoration)
        if unresolved:
            raise ValueError(
                "canonical heavy restoration unresolved for generated plan: "
                + "; ".join(unresolved)
            )

        event_by_action = {
            (float(item.action.time_seconds), int(item.action.sequence)): item.restoration_event
            for item in restoration.resolutions
            if item.restoration_event is not None
            and item.restoration_event.resource is resource
        }

        def resolve(action: RotationAction):
            return event_by_action.get((float(action.time_seconds), int(action.sequence)))

        return resolve

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
        restoration = self._restoration_projection(
            character_build=character_build,
            sustain_build=sustain_build,
            plan=plan,
            initial_bar=initial_bar,
            completion_evidence=completion_evidence,
        )

        unresolved = self._restoration_unresolved(restoration)
        if unresolved:
            return RotationHeavySustainProjection(
                restoration_projection=restoration,
                replay=None,
                unresolved=unresolved,
            )

        resolve = self.restoration_resolver_for_plan(
            character_build=character_build,
            sustain_build=sustain_build,
            plan=plan,
            resource=resource,
            initial_bar=initial_bar,
            completion_evidence=completion_evidence,
        )
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

    def _restoration_projection(
        self,
        *,
        character_build: CharacterBuild,
        sustain_build: PlayerBuild,
        plan: RotationPlan,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
    ) -> RotationHeavyAttackRestorationProjection:
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

        return self.restoration_service.project(
            build=character_build,
            plan=plan,
            initial_bar=initial_bar,
            completion_evidence=tuple(completion_evidence),
            modifier_resolver=resolve_modifiers,
        )

    @classmethod
    def _restoration_unresolved(
        cls,
        restoration: RotationHeavyAttackRestorationProjection,
    ) -> tuple[str, ...]:
        unresolved = list(restoration.unresolved)
        unresolved.extend(
            f"heavy-attack weapon projection violation at "
            f"{item.action.time_seconds:.3f}s sequence {item.action.sequence}: {item.reason}"
            for item in restoration.weapon_projection.violations
        )
        return cls._dedupe(tuple(unresolved))

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
