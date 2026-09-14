from __future__ import annotations

"""Search named-gear structure while external mechanics retain semantic ownership.

Some objective-relevant named sets are intentionally classified outside the ordinary
exact-flat gear scorer because their effects are conditional, percentage based,
formula driven, or otherwise runtime-sensitive. Higher proof layers still need to
ask a purely structural question: can this exact named set occupy a legal loadout
alongside the ordinary objective winner?

This adapter derives a search-only relevance view in which explicitly externalized
set breakpoints are zero-delta structural carriers. It never rewrites canonical
mechanics and never exposes that zero as the set's real objective contribution. The
caller remains responsible for applying the owning special-mechanic service afterward.

Upstream relevance diagnostics are preserved on the result, but they do not poison
the local structural proof. Unexternalized special rows remain special/non-flat
candidate pairs and therefore stay excluded from the exact-flat search itself.
"""

from dataclasses import dataclass, replace

from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeConstrainedNamedGearExactFlatSearchResult,
    ExtremeConstrainedNamedGearExactFlatSearchService,
    ExtremeNamedGearRequirement,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointCatalog
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


@dataclass(frozen=True)
class ExtremeExternalizedNamedGearSemantic:
    set_name: str
    piece_count: int


@dataclass(frozen=True)
class ExtremeExternalizedNamedGearConstraintSearchResult:
    search: ExtremeConstrainedNamedGearExactFlatSearchResult | None
    externalized: tuple[ExtremeExternalizedNamedGearSemantic, ...]
    unresolved: tuple[str, ...] = ()
    upstream_unresolved: tuple[str, ...] = ()

    @property
    def winner_found(self) -> bool:
        return bool(self.search is not None and self.search.winner_found and not self.unresolved)


class ExtremeExternalizedNamedGearConstraintSearchService:
    """Reuse exact-flat structure search without stealing special-effect ownership."""

    @staticmethod
    def _derived_relevance(
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
        externalized: tuple[ExtremeExternalizedNamedGearSemantic, ...],
    ) -> tuple[ExtremeGearSetObjectiveRelevanceCatalog | None, tuple[str, ...]]:
        by_name: dict[str, list[int]] = {}
        for row in eligibility.sets:
            by_name.setdefault(row.name.strip().casefold(), []).append(int(row.set_id))

        targets: set[tuple[int, int]] = set()
        unresolved: list[str] = []
        for item in externalized:
            name = str(item.set_name or "").strip()
            count = int(item.piece_count)
            matches = tuple(by_name.get(name.casefold(), ()))
            if len(matches) != 1:
                unresolved.append(
                    f"Externalized named set {name!r} resolved to {len(matches)} canonical eligibility rows"
                )
                continue
            targets.add((matches[0], count))

        if unresolved:
            return None, tuple(dict.fromkeys(unresolved))

        evidence_by_pair = {
            (int(row.set_id), int(row.piece_count)): row for row in relevance.evidence
        }
        missing = tuple(pair for pair in sorted(targets) if pair not in evidence_by_pair)
        if missing:
            return None, tuple(
                f"Externalized named set pair {pair!r} has no objective relevance evidence"
                for pair in missing
            )

        rows = []
        for row in relevance.evidence:
            pair = (int(row.set_id), int(row.piece_count))
            if pair not in targets:
                rows.append(row)
                continue
            candidate = replace(
                row.candidate,
                reviewed_delta=0.0,
                source_effects=(),
                unresolved=(),
            )
            rows.append(
                replace(
                    row,
                    status=ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT,
                    reviewed_delta=0.0,
                    candidate=candidate,
                    search_state_rule=None,
                )
            )

        return (
            ExtremeGearSetObjectiveRelevanceCatalog(
                objective_key=relevance.objective_key,
                evidence=tuple(rows),
                unresolved=(),
            ),
            (),
        )

    @classmethod
    def search(
        cls,
        *,
        topology_catalog: ExtremeGearSetTopologyCatalog,
        breakpoints: ExtremeGearSetBonusBreakpointCatalog,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
        requirements: tuple[ExtremeNamedGearRequirement, ...],
        externalized: tuple[ExtremeExternalizedNamedGearSemantic, ...],
    ) -> ExtremeExternalizedNamedGearConstraintSearchResult:
        derived, unresolved = cls._derived_relevance(relevance, eligibility, externalized)
        if derived is None:
            return ExtremeExternalizedNamedGearConstraintSearchResult(
                search=None,
                externalized=externalized,
                unresolved=unresolved,
                upstream_unresolved=tuple(relevance.unresolved),
            )
        search = ExtremeConstrainedNamedGearExactFlatSearchService(
            breakpoints=breakpoints,
            eligibility=eligibility,
            relevance=derived,
            requirements=requirements,
        ).search(topology_catalog)
        return ExtremeExternalizedNamedGearConstraintSearchResult(
            search=search,
            externalized=externalized,
            unresolved=tuple(search.unresolved),
            upstream_unresolved=tuple(relevance.unresolved),
        )


__all__ = [
    "ExtremeExternalizedNamedGearConstraintSearchResult",
    "ExtremeExternalizedNamedGearConstraintSearchService",
    "ExtremeExternalizedNamedGearSemantic",
]
