from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Protocol

from engine.config import get_data_dir
from minmax.evaluation_context import EvaluationContext
from minmax.rotation_plan import RotationAction, RotationActionKind
from models.build_model import PlayerBuild
from services.rotation_active_bar_context_resolver_service import (
    RotationActiveBarContextResolverService,
)
from services.rotation_candidate_action_damage_evidence_service import (
    RotationActionDamageProvider,
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationCandidateDDRoleOutputService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_light_attack_damage_evidence_service import (
    RotationCandidateLightAttackDamageEvidenceService,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_candidate_ultimate_damage_evidence_service import (
    RotationCandidateUltimateDamageEvidenceService,
)
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationSavedBuildWeaponAttackEvaluationService,
    RotationWeaponAttackBuildEvaluationResolution,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage_dealer"}


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class RotationGenerateDDWeaponAttackProviderFactory(Protocol):
    """Supply verified LA/HA evaluators from one canonical saved-build evaluation."""

    def providers_for(
        self,
        *,
        player_build: PlayerBuild,
        static_context,
        target_resistance: float,
    ) -> tuple[
        RotationActionDamageProvider | None,
        RotationActionDamageProvider | None,
    ]: ...


class _RotationGenerateBarAwareSkillDamageProvider:
    """Evaluate one skill against the static context active at its exact plan point."""

    def __init__(
        self,
        *,
        database_path: Path,
        static_context,
        target_resistance: float,
    ) -> None:
        self.database_path = database_path
        self.static_context = static_context
        self.target_resistance = float(target_resistance)

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.SKILL:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} damage requires its dedicated canonical action evaluator",
                ),
            )

        resolver = RotationActiveBarContextResolverService(
            static_context=self.static_context,
            plan=candidate.plan,
        )
        context = resolver.context_at(action.time_seconds, action.sequence)
        context = replace(
            context,
            target_resistance=self.target_resistance,
            fight_duration=float(candidate.plan.duration_seconds),
        )
        return RotationCandidateSkillDamageEvidenceService(
            database_path=self.database_path,
            context=context,
        ).evaluate_action(
            candidate=candidate,
            action=action,
        )


class _RotationGenerateBarAwareLightAttackDamageProvider:
    """Evaluate each light attack from the canonical build state active on its bar."""

    def __init__(
        self,
        *,
        evaluation: RotationWeaponAttackBuildEvaluationResolution,
        static_context,
        target_resistance: float,
    ) -> None:
        if not evaluation.resolved or evaluation.build is None:
            raise ValueError("bar-aware light-attack provider requires resolved weapon-attack evaluation")
        self.evaluation = evaluation
        self.static_context = static_context
        self.target_resistance = float(target_resistance)

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.LIGHT_ATTACK:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{action.kind.value} is not a light attack for light-attack damage evaluation",
                ),
            )

        resolver = RotationActiveBarContextResolverService(
            static_context=self.static_context,
            plan=candidate.plan,
        )
        context = resolver.context_at(action.time_seconds, action.sequence)
        build_evaluation = self.evaluation.evaluation_for(context.active_bar)
        if build_evaluation is None:
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=(
                    f"{context.active_bar} canonical weapon-attack BuildEvaluation is unavailable",
                ),
            )

        return RotationCandidateLightAttackDamageEvidenceService(
            build=self.evaluation.build,
            evaluation=build_evaluation,
            initial_bar="front",
            evaluation_context=EvaluationContext(
                fight_duration=float(candidate.plan.duration_seconds),
                target_resistance=self.target_resistance,
            ),
        ).evaluate_action(
            candidate=candidate,
            action=action,
        )


class _RotationGenerateUnresolvedWeaponAttackProvider:
    """Preserve bridge failures as action-local unresolved evidence."""

    def __init__(self, unresolved: tuple[str, ...]) -> None:
        self.unresolved = tuple(
            dict.fromkeys(
                str(item).strip() for item in unresolved if str(item).strip()
            )
        ) or ("canonical weapon-attack evaluation is unresolved",)

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=self.unresolved,
        )


class RotationGenerateDDCanonicalWeaponAttackProviderFactory:
    """Production bridge from saved-build canonical state to weapon-attack providers.

    Light attacks are fully composed through the reviewed canonical LA calculator.
    Heavy attacks deliberately remain unresolved here until candidate-specific
    full-charge/completion evidence is connected to the same factory.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        evaluation_service: RotationSavedBuildWeaponAttackEvaluationService | None = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.evaluation_service = (
            evaluation_service
            or RotationSavedBuildWeaponAttackEvaluationService(self.database_path)
        )

    def providers_for(
        self,
        *,
        player_build: PlayerBuild,
        static_context,
        target_resistance: float,
    ) -> tuple[
        RotationActionDamageProvider | None,
        RotationActionDamageProvider | None,
    ]:
        resolution = self.evaluation_service.resolve(
            player_build=player_build,
            static_context=static_context,
        )
        if not resolution.resolved:
            return (
                _RotationGenerateUnresolvedWeaponAttackProvider(resolution.unresolved),
                None,
            )
        return (
            _RotationGenerateBarAwareLightAttackDamageProvider(
                evaluation=resolution,
                static_context=static_context,
                target_resistance=target_resistance,
            ),
            None,
        )


class RotationGenerateDDRoleEvidenceSupport:
    """Compose fail-closed canonical DD role output for Generate candidates.

    Skill and Ultimate damage reuse the existing candidate action-damage authorities.
    Each skill is evaluated from the static front/back context active at its exact
    ``(time_seconds, sequence)`` point. Target resistance must be explicit evidence.

    Existing canonical light/heavy-attack evaluators participate only through a
    verified weapon-attack provider factory. The production factory now bridges
    canonical saved-build static state into bar-aware Light Attack evaluation.
    Heavy attacks remain fail-closed until candidate-specific completion/full-charge
    evidence is attached. Periodic skill components likewise stay unresolved unless
    their reviewed runtime semantics are supplied by the canonical skill-damage authority.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        static_context_service: RotationStaticBuildContextService | None = None,
        weapon_attack_provider_factory: (
            RotationGenerateDDWeaponAttackProviderFactory | None
        ) = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.static_context_service = (
            static_context_service or RotationStaticBuildContextService()
        )
        self.weapon_attack_provider_factory = weapon_attack_provider_factory

    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence:
        role_key = _canonical_role(getattr(player_build, "Role", ""))
        if role_key not in _DD_ROLE_KEYS:
            raise ValueError(
                "automatic DD role evidence requires an explicit damage-dealer saved-build role"
            )
        if evidence_bundle.target_resistance is None:
            raise ValueError(
                "automatic DD role evidence requires explicit target resistance"
            )

        static_context = self.static_context_service.resolve(player_build)
        if not static_context.resolved:
            detail = "; ".join(static_context.unresolved) or "static build context unavailable"
            raise ValueError("canonical DD static build evidence is unresolved: " + detail)

        target_resistance = float(evidence_bundle.target_resistance)
        skill_provider = _RotationGenerateBarAwareSkillDamageProvider(
            database_path=self.database_path,
            static_context=static_context,
            target_resistance=target_resistance,
        )
        ultimate_provider = RotationCandidateUltimateDamageEvidenceService(
            skill_damage_delegate=skill_provider,
        )

        light_attack_provider: RotationActionDamageProvider | None = None
        heavy_attack_provider: RotationActionDamageProvider | None = None
        if self.weapon_attack_provider_factory is not None:
            light_attack_provider, heavy_attack_provider = (
                self.weapon_attack_provider_factory.providers_for(
                    player_build=player_build,
                    static_context=static_context,
                    target_resistance=target_resistance,
                )
            )

        action_router = RotationCandidateActionDamageEvidenceService(
            skill_provider=skill_provider,
            light_attack_provider=light_attack_provider,
            heavy_attack_provider=heavy_attack_provider,
            ultimate_provider=ultimate_provider,
        )
        role_output = RotationCandidateDDRoleOutputService(
            action_damage_evidence_provider=action_router,
        )
        plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
            build=player_build,
            resource=evidence_bundle.resource,
            role_output_evidence_provider=role_output,
        )
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=plan_evidence,
            role_output_label="projected DPS",
            assigned_support_label="assigned support coverage",
            content_type=str(evidence_bundle.content_type or "").strip(),
            role_key=role_key,
        )


__all__ = [
    "RotationGenerateDDCanonicalWeaponAttackProviderFactory",
    "RotationGenerateDDRoleEvidenceSupport",
    "RotationGenerateDDWeaponAttackProviderFactory",
]
