from __future__ import annotations

"""Proof-reduce provisioning witnesses for one concrete Extreme gear realization.

The global provisioning projection intentionally retains one strongest food and one
strongest drink so runtime conditions such as ``food_buff_active`` and
``drink_buff_active`` remain representable. Most gear realizations do not carry a
set whose target-resource bonus depends on provisioning kind, however. For those
candidates the weaker static provisioning witness is dominated and only the stronger
static witness needs canonical scoring.

If the realization activates any reviewed food/drink-dependent target-resource set,
this service deliberately retains the full global food+drink frontier. The
conditional set bonus can change which kind wins, so canonical scoring must decide
that tradeoff. Any incomplete proof also falls back to the global frontier.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from minmax.effects import EffectOperation
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjection,
    ExtremeResourceProvisioningProjectionService,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeCoverageAudit,
    ExtremeResourceRuntimeCoverageAuditService,
)


_TARGET_STAT = {
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}
_KIND_CONDITIONS = frozenset({"food_buff_active", "drink_buff_active"})


class _ProvisioningProjectionProvider(Protocol):
    def build(self, objective_key: str) -> ExtremeResourceProvisioningProjection: ...


class _RuntimeAuditProvider(Protocol):
    def build(self, objective_key: str) -> ExtremeResourceRuntimeCoverageAudit: ...


@dataclass(frozen=True)
class ExtremeResourceCandidateProvisioningProjection:
    objective_key: str
    global_choices: tuple[str, ...]
    choices: tuple[str, ...]
    active_kind_conditions: tuple[str, ...]
    denominator_proven: bool
    reduced: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(self.denominator_proven and self.choices and not self.unresolved)


class ExtremeResourceCandidateProvisioningProjectionService:
    """Collapse food+drink to one witness when provisioning kind is irrelevant."""

    SUPPORTED_OBJECTIVES = frozenset(_TARGET_STAT)

    def __init__(
        self,
        repository: ProvisioningStaticRepository,
        *,
        database_path: str | Path | None = None,
        provisioning_projection_service: _ProvisioningProjectionProvider | None = None,
        runtime_audit_service: _RuntimeAuditProvider | None = None,
    ) -> None:
        self.repository = repository
        self.provisioning_projection_service = (
            provisioning_projection_service
            or ExtremeResourceProvisioningProjectionService(repository)
        )
        resolved_database = database_path or getattr(repository, "database_path", None)
        if runtime_audit_service is None and resolved_database is None:
            raise ValueError(
                "database_path is required when no runtime audit service is supplied"
            )
        self.runtime_audit_service = (
            runtime_audit_service
            or ExtremeResourceRuntimeCoverageAuditService(resolved_database)
        )
        self._static_score_cache: dict[tuple[str, str], float | None] = {}

    @staticmethod
    def _active_set_counts(
        realization: ExtremeNamedGearSetRealization,
    ) -> dict[str, int]:
        return {
            str(name): int(count)
            for name, count in zip(realization.set_names, realization.counts)
        }

    def _static_score(self, objective_key: str, name: str) -> float | None:
        cache_key = (objective_key, str(name))
        if cache_key in self._static_score_cache:
            return self._static_score_cache[cache_key]

        target = _TARGET_STAT[objective_key]
        effects, unresolved = self.repository.resolve(name)
        if unresolved:
            self._static_score_cache[cache_key] = None
            return None

        value = 0.0
        for effect in effects:
            if effect.stat is not target:
                continue
            if effect.operation is not EffectOperation.ADD:
                self._static_score_cache[cache_key] = None
                return None
            value += float(effect.value)

        self._static_score_cache[cache_key] = value
        return value

    def build(
        self,
        objective_key: str,
        realization: ExtremeNamedGearSetRealization,
    ) -> ExtremeResourceCandidateProvisioningProjection:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(
                f"unreviewed Extreme candidate provisioning objective: {objective_key!r}"
            )

        global_projection = self.provisioning_projection_service.build(key)
        global_choices = tuple(global_projection.choices)
        fallback = ExtremeResourceCandidateProvisioningProjection(
            objective_key=key,
            global_choices=global_choices,
            choices=global_choices,
            active_kind_conditions=(),
            denominator_proven=bool(global_projection.projection_complete),
            reduced=False,
            unresolved=tuple(global_projection.unresolved),
        )
        if not global_projection.projection_complete or not global_choices:
            return fallback

        audit = self.runtime_audit_service.build(key)
        if not audit.denominator_proven or audit.unresolved:
            return ExtremeResourceCandidateProvisioningProjection(
                objective_key=key,
                global_choices=global_choices,
                choices=global_choices,
                active_kind_conditions=(),
                denominator_proven=False,
                reduced=False,
                unresolved=tuple(audit.unresolved),
            )

        counts = self._active_set_counts(realization)
        active_kind_conditions = tuple(
            sorted(
                {
                    row.condition
                    for row in audit.conditional_gear_effects
                    if row.condition in _KIND_CONDITIONS
                    and int(counts.get(row.set_name, 0)) >= int(row.piece_count)
                },
                key=str.casefold,
            )
        )
        if active_kind_conditions:
            return ExtremeResourceCandidateProvisioningProjection(
                objective_key=key,
                global_choices=global_choices,
                choices=global_choices,
                active_kind_conditions=active_kind_conditions,
                denominator_proven=True,
                reduced=False,
            )

        scored: list[tuple[float, str]] = []
        for name in global_choices:
            value = self._static_score(key, name)
            if value is None:
                return fallback
            scored.append((value, name))

        if not scored:
            return fallback
        scored.sort(key=lambda item: (-item[0], item[1].casefold(), item[1]))
        winner = scored[0][1]
        return ExtremeResourceCandidateProvisioningProjection(
            objective_key=key,
            global_choices=global_choices,
            choices=(winner,),
            active_kind_conditions=(),
            denominator_proven=True,
            reduced=len(global_choices) > 1,
        )


__all__ = [
    "ExtremeResourceCandidateProvisioningProjection",
    "ExtremeResourceCandidateProvisioningProjectionService",
]
