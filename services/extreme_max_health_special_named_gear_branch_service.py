from __future__ import annotations

"""Classify special Max Health named-gear branches into explicit proof obligations.

The ordinary max-resource named-gear branch-and-bound service deliberately excludes
conditional effects and search-space mutators. This layer does not score those
branches. It converts every excluded Max Health breakpoint into structured,
reviewable evidence describing the mechanic that a higher search layer must execute.

A named-set breakpoint may contain the cumulative effects from earlier piece counts.
Therefore a special 5-piece branch is a reviewed *effect bundle*, not necessarily one
isolated effect. Unconditional flat Max Health effects may coexist with one or more
conditional flat/percent effects; the latter become explicit runtime obligations.

No set-name allowlist lives here. Classification comes from canonical relevance
and effect evidence so newly reviewed sets follow the same contract automatically.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)


class ExtremeMaxHealthSpecialBranchKind(str, Enum):
    CONDITIONAL_FLAT = "conditional_flat"
    CONDITIONAL_PERCENT = "conditional_percent"
    CONDITIONAL_BUNDLE = "conditional_bundle"
    SEARCH_STATE_MUTATION = "search_state_mutation"


@dataclass(frozen=True)
class ExtremeMaxHealthSpecialNamedGearBranch:
    set_id: int
    set_name: str
    piece_count: int
    kind: ExtremeMaxHealthSpecialBranchKind
    value: float | None = None
    condition: str | None = None
    unit: EffectUnit | None = None
    search_state_rule: ExtremeGearSearchStateRule | None = None
    target_effects: tuple[Effect, ...] = ()
    required_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeMaxHealthSpecialNamedGearBranchResult:
    branches: tuple[ExtremeMaxHealthSpecialNamedGearBranch, ...]
    requested_pairs: tuple[tuple[int, str, int], ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_classified(self) -> bool:
        return not self.unresolved and len(self.branches) == len(self.requested_pairs)


class ExtremeMaxHealthSpecialNamedGearBranchService:
    """Translate excluded Max Health gear pairs into explicit mechanic obligations."""

    OBJECTIVE_KEY = "max_health"

    def __init__(self, relevance: ExtremeGearSetObjectiveRelevanceCatalog) -> None:
        objective = str(relevance.objective_key or "").strip().casefold()
        if objective != self.OBJECTIVE_KEY:
            raise ValueError("special named-gear branch classification currently supports max_health only")
        self.relevance = relevance

    @staticmethod
    def _max_health_effects(
        evidence: ExtremeGearSetObjectiveBreakpointEvidence,
    ) -> tuple[Effect, ...]:
        return tuple(
            effect
            for effect in evidence.candidate.source_effects
            if effect.stat is StatId.MAX_HEALTH
        )

    @classmethod
    def _classify(
        cls,
        evidence: ExtremeGearSetObjectiveBreakpointEvidence,
    ) -> ExtremeMaxHealthSpecialNamedGearBranch | str:
        if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            return (
                f"{evidence.set_name} ({evidence.piece_count}) was requested as a special "
                "branch but objective relevance marks it proven irrelevant"
            )

        if evidence.search_state_rule is not None:
            return ExtremeMaxHealthSpecialNamedGearBranch(
                set_id=int(evidence.set_id),
                set_name=str(evidence.set_name),
                piece_count=int(evidence.piece_count),
                kind=ExtremeMaxHealthSpecialBranchKind.SEARCH_STATE_MUTATION,
                search_state_rule=evidence.search_state_rule,
                target_effects=cls._max_health_effects(evidence),
            )

        effects = cls._max_health_effects(evidence)
        if not effects:
            return (
                f"{evidence.set_name} ({evidence.piece_count}) has no reviewed Max Health "
                "effects for special branch execution"
            )

        conditional: list[Effect] = []
        for effect in effects:
            condition = str(effect.condition or "").strip()
            if effect.operation is EffectOperation.ADD:
                # Cumulative earlier-breakpoint flat bonuses are legal baseline
                # contributions. Only conditioned ADD effects create runtime work.
                if condition:
                    conditional.append(effect)
                continue
            if effect.operation is EffectOperation.ADD_PERCENT:
                # Percentage effects are retained in the special bundle. They may be
                # conditional (Armor Master) or unconditional; canonical scoring owns
                # their arithmetic rather than flattening them into reviewed_delta.
                conditional.append(effect)
                continue
            return (
                f"{evidence.set_name} ({evidence.piece_count}) uses unsupported special "
                f"Max Health operation {effect.operation.value}"
            )

        if not conditional:
            return (
                f"{evidence.set_name} ({evidence.piece_count}) special Max Health bundle "
                "contains no conditional or percentage effect"
            )

        conditions = tuple(
            dict.fromkeys(
                str(effect.condition or "").strip()
                for effect in conditional
                if str(effect.condition or "").strip()
            )
        )
        operations = {effect.operation for effect in conditional}
        if len(effects) == 1 and operations == {EffectOperation.ADD}:
            kind = ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_FLAT
        elif len(effects) == 1 and operations == {EffectOperation.ADD_PERCENT}:
            kind = ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_PERCENT
        else:
            kind = ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_BUNDLE

        # Preserve the legacy scalar fields only when the special obligation is a
        # single effect. Bundle consumers must use target_effects/required_conditions.
        single = conditional[0] if len(conditional) == 1 else None
        return ExtremeMaxHealthSpecialNamedGearBranch(
            set_id=int(evidence.set_id),
            set_name=str(evidence.set_name),
            piece_count=int(evidence.piece_count),
            kind=kind,
            value=(None if single is None else float(single.value)),
            condition=(None if single is None else str(single.condition or "").strip() or None),
            unit=(None if single is None else single.unit),
            target_effects=effects,
            required_conditions=conditions,
        )

    def build(
        self,
        requested_pairs: tuple[tuple[int, str, int], ...],
    ) -> ExtremeMaxHealthSpecialNamedGearBranchResult:
        normalized = tuple(
            sorted(
                {
                    (int(set_id), str(name), int(piece_count))
                    for set_id, name, piece_count in requested_pairs
                },
                key=lambda row: (row[2], row[0], row[1].casefold(), row[1]),
            )
        )
        evidence_by_key = {
            (int(row.set_id), int(row.piece_count)): row
            for row in self.relevance.evidence
        }

        branches: list[ExtremeMaxHealthSpecialNamedGearBranch] = []
        unresolved: list[str] = list(self.relevance.unresolved)
        for set_id, name, piece_count in normalized:
            evidence = evidence_by_key.get((set_id, piece_count))
            if evidence is None:
                unresolved.append(
                    f"{name} ({piece_count}) has no canonical Max Health relevance evidence"
                )
                continue
            classified = self._classify(evidence)
            if isinstance(classified, str):
                unresolved.append(classified)
                continue
            branches.append(classified)

        branches.sort(
            key=lambda row: (row.piece_count, row.set_id, row.set_name.casefold(), row.set_name)
        )
        return ExtremeMaxHealthSpecialNamedGearBranchResult(
            branches=tuple(branches),
            requested_pairs=normalized,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeMaxHealthSpecialBranchKind",
    "ExtremeMaxHealthSpecialNamedGearBranch",
    "ExtremeMaxHealthSpecialNamedGearBranchResult",
    "ExtremeMaxHealthSpecialNamedGearBranchService",
]
