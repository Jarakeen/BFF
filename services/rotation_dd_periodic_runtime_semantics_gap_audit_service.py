from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from models.build_model import PlayerBuild
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)


@dataclass(frozen=True)
class RotationDDPeriodicRuntimeSemanticsGap:
    """One verified periodic damage component still missing reviewed runtime semantics."""

    skill_entity_id: str
    skill_rank_id: int
    coefficient_number: int
    classification_source: str = ""


@dataclass(frozen=True)
class RotationDDPeriodicRuntimeSemanticsGapAudit:
    """Reviewed, missing, and unresolved periodic-semantics evidence for requested skills."""

    reviewed: tuple[RotationPeriodicDamageRuntimeSemantics, ...]
    missing: tuple[RotationDDPeriodicRuntimeSemanticsGap, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.missing and not self.unresolved


class RotationDDPeriodicRuntimeSemanticsGapAuditService:
    """Build a finite review queue for DD periodic runtime semantics.

    Requested skills are normalized to canonical lower-snake-case ability identity.
    Numeric ESO ability IDs remain repository crosswalk details and are never used as
    the durable audit key. Only components explicitly classified as damage + DoT are
    eligible for the missing-semantics queue. Unknown periodic identity stays
    unresolved rather than being guessed from duration, tooltip prose, or names.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        component_repository: SkillComponentRepository | None = None,
        semantics_registry: RotationDDPeriodicRuntimeSemanticsRegistryService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.components = component_repository or SkillComponentRepository(
            self.database_path
        )
        self.semantics_registry = (
            semantics_registry or RotationDDPeriodicRuntimeSemanticsRegistryService()
        )

    def audit_build(
        self,
        player_build: PlayerBuild,
    ) -> RotationDDPeriodicRuntimeSemanticsGapAudit:
        """Audit the canonical skill identities saved on both bars of one build.

        Bar order and duplicate slots do not change periodic runtime semantics, so
        this adapter delegates to ``audit`` after collecting the saved skill names.
        Ultimates are included because the sixth saved slot shares the same canonical
        skill identity path as ordinary skills; non-periodic components are filtered
        by verified component classification below.

        Minimal/legacy build-like objects may omit one or both bar fields. Missing
        bars contribute no skill identities instead of turning an evidence audit into
        an attribute error.
        """

        front = tuple(getattr(player_build, "FrontBarSkills", ()) or ())
        back = tuple(getattr(player_build, "BackBarSkills", ()) or ())
        return self.audit(front + back)

    def audit(
        self,
        skill_entity_ids: Iterable[str],
    ) -> RotationDDPeriodicRuntimeSemanticsGapAudit:
        requested = tuple(
            dict.fromkeys(
                ability_entity_id(item)
                for item in skill_entity_ids
                if ability_entity_id(item)
            )
        )
        reviewed_registry = self.semantics_registry.load()
        reviewed_by_key = {
            (item.skill_entity_id, item.coefficient_number): item
            for item in reviewed_registry
        }

        reviewed: list[RotationPeriodicDamageRuntimeSemantics] = []
        missing: list[RotationDDPeriodicRuntimeSemanticsGap] = []
        unresolved: list[str] = []

        for entity_id in requested:
            resolution = self.coefficients.resolve_entity_id(entity_id)
            if resolution.rank is None:
                details = resolution.unresolved or (
                    f"canonical skill identity {entity_id!r} did not resolve",
                )
                unresolved.extend(str(item).strip() for item in details if str(item).strip())
                continue
            if resolution.unresolved:
                unresolved.extend(
                    f"{entity_id}: {str(item).strip()}"
                    for item in resolution.unresolved
                    if str(item).strip()
                )

            rank = resolution.rank
            components = self.components.get_for_skill_rank(rank.skill_rank_id)
            if not components:
                unresolved.append(
                    f"{entity_id}: component classification is unavailable for skill rank {rank.skill_rank_id}"
                )
                continue

            for component in components:
                if component.effect_kind is not SkillEffectKind.DAMAGE:
                    continue
                if component.is_dot is None:
                    unresolved.append(
                        f"{entity_id}: coefficient {component.coefficient_number} damage periodic identity is unresolved"
                    )
                    continue
                if not component.is_dot:
                    continue

                key = (entity_id, component.coefficient_number)
                semantic = reviewed_by_key.get(key)
                if semantic is not None:
                    reviewed.append(semantic)
                    continue
                missing.append(
                    RotationDDPeriodicRuntimeSemanticsGap(
                        skill_entity_id=entity_id,
                        skill_rank_id=rank.skill_rank_id,
                        coefficient_number=component.coefficient_number,
                        classification_source=str(component.source or "").strip(),
                    )
                )

        return RotationDDPeriodicRuntimeSemanticsGapAudit(
            reviewed=tuple(reviewed),
            missing=tuple(missing),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationDDPeriodicRuntimeSemanticsGap",
    "RotationDDPeriodicRuntimeSemanticsGapAudit",
    "RotationDDPeriodicRuntimeSemanticsGapAuditService",
]
