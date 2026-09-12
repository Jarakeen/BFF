from __future__ import annotations

"""Classify special Max-resource named-gear branches into proof obligations.

The ordinary max-resource named-gear search deliberately excludes conditional,
percentage, and search-state-mutating breakpoints. This service converts those
excluded pairs into structured obligations for max_health, max_magicka, and
max_stamina without relying on set-name allowlists.
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


class ExtremeMaxResourceSpecialBranchKind(str, Enum):
    CONDITIONAL_FLAT = "conditional_flat"
    CONDITIONAL_PERCENT = "conditional_percent"
    CONDITIONAL_BUNDLE = "conditional_bundle"
    SEARCH_STATE_MUTATION = "search_state_mutation"


_OBJECTIVE_STATS = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}

_OBJECTIVE_LABELS = {
    "max_health": "Max Health",
    "max_magicka": "Max Magicka",
    "max_stamina": "Max Stamina",
}


@dataclass(frozen=True)
class ExtremeMaxResourceSpecialNamedGearBranch:
    objective_key: str
    set_id: int
    set_name: str
    piece_count: int
    kind: ExtremeMaxResourceSpecialBranchKind
    value: float | None = None
    condition: str | None = None
    unit: EffectUnit | None = None
    search_state_rule: ExtremeGearSearchStateRule | None = None
    target_effects: tuple[Effect, ...] = ()
    required_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeMaxResourceSpecialNamedGearBranchResult:
    objective_key: str
    branches: tuple[ExtremeMaxResourceSpecialNamedGearBranch, ...]
    requested_pairs: tuple[tuple[int, str, int], ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_classified(self) -> bool:
        return not self.unresolved and len(self.branches) == len(self.requested_pairs)


class ExtremeMaxResourceSpecialNamedGearBranchService:
    """Translate excluded max-resource gear pairs into explicit mechanic obligations."""

    SUPPORTED_OBJECTIVES = frozenset(_OBJECTIVE_STATS)

    def __init__(self, relevance: ExtremeGearSetObjectiveRelevanceCatalog) -> None:
        objective = str(relevance.objective_key or "").strip().casefold()
        if objective not in self.SUPPORTED_OBJECTIVES:
            raise ValueError(
                f"special named-gear branch classification does not support {relevance.objective_key!r}"
            )
        self.objective_key = objective
        self.objective_stat = _OBJECTIVE_STATS[objective]
        self.objective_label = _OBJECTIVE_LABELS[objective]
        self.relevance = relevance

    def _target_effects(
        self,
        evidence: ExtremeGearSetObjectiveBreakpointEvidence,
    ) -> tuple[Effect, ...]:
        return tuple(
            effect
            for effect in evidence.candidate.source_effects
            if effect.stat is self.objective_stat
        )

    def _classify(
        self,
        evidence: ExtremeGearSetObjectiveBreakpointEvidence,
    ) -> ExtremeMaxResourceSpecialNamedGearBranch | str:
        if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
            return (
                f"{evidence.set_name} ({evidence.piece_count}) was requested as a special "
                "branch but objective relevance marks it proven irrelevant"
            )

        effects = self._target_effects(evidence)
        if evidence.search_state_rule is not None:
            return ExtremeMaxResourceSpecialNamedGearBranch(
                objective_key=self.objective_key,
                set_id=int(evidence.set_id),
                set_name=str(evidence.set_name),
                piece_count=int(evidence.piece_count),
                kind=ExtremeMaxResourceSpecialBranchKind.SEARCH_STATE_MUTATION,
                search_state_rule=evidence.search_state_rule,
                target_effects=effects,
            )

        if not effects:
            return (
                f"{evidence.set_name} ({evidence.piece_count}) has no reviewed "
                f"{self.objective_label} effects for special branch execution"
            )

        conditional: list[Effect] = []
        for effect in effects:
            condition = str(effect.condition or "").strip()
            if effect.operation is EffectOperation.ADD:
                if condition:
                    conditional.append(effect)
                continue
            if effect.operation is EffectOperation.ADD_PERCENT:
                conditional.append(effect)
                continue
            return (
                f"{evidence.set_name} ({evidence.piece_count}) uses unsupported special "
                f"{self.objective_label} operation {effect.operation.value}"
            )

        if not conditional:
            return (
                f"{evidence.set_name} ({evidence.piece_count}) special {self.objective_label} "
                "bundle contains no conditional or percentage effect"
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
            kind = ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_FLAT
        elif len(effects) == 1 and operations == {EffectOperation.ADD_PERCENT}:
            kind = ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_PERCENT
        else:
            kind = ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_BUNDLE

        single = conditional[0] if len(conditional) == 1 else None
        return ExtremeMaxResourceSpecialNamedGearBranch(
            objective_key=self.objective_key,
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
    ) -> ExtremeMaxResourceSpecialNamedGearBranchResult:
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

        branches: list[ExtremeMaxResourceSpecialNamedGearBranch] = []
        unresolved: list[str] = list(self.relevance.unresolved)
        for set_id, name, piece_count in normalized:
            evidence = evidence_by_key.get((set_id, piece_count))
            if evidence is None:
                unresolved.append(
                    f"{name} ({piece_count}) has no canonical {self.objective_label} relevance evidence"
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
        return ExtremeMaxResourceSpecialNamedGearBranchResult(
            objective_key=self.objective_key,
            branches=tuple(branches),
            requested_pairs=normalized,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeMaxResourceSpecialBranchKind",
    "ExtremeMaxResourceSpecialNamedGearBranch",
    "ExtremeMaxResourceSpecialNamedGearBranchResult",
    "ExtremeMaxResourceSpecialNamedGearBranchService",
]
