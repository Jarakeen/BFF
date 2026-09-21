from __future__ import annotations

"""Explicit finite runtime-state families for generated sustained-DPS search.

The runtime-state universe is not inferred here. A caller may provide a finite family
only when it can separately prove that family is the complete denominator for the
branch being searched. The service preserves omitted scope so local closure cannot be
mistaken for global runtime closure.
"""

from dataclasses import dataclass

from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeStateChoice:
    runtime_state_id: str
    snapshot: ExtremeRuntimeSnapshot
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        value = str(self.runtime_state_id or "").strip()
        if not value:
            raise ValueError("runtime-state choice requires runtime_state_id")
        object.__setattr__(self, "runtime_state_id", value)
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeStateFrontier:
    choices: tuple[ExtremeSustainedDPSRuntimeStateChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    omitted_scope: tuple[str, ...]


class ExtremeSustainedDPSRuntimeStateFrontierService:
    """Validate one externally closed finite runtime-state family."""

    @classmethod
    def build(
        cls,
        choices: tuple[ExtremeSustainedDPSRuntimeStateChoice, ...],
        *,
        denominator_proven: bool,
        source: str,
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeStateFrontier:
        unresolved: list[str] = []
        seen: set[str] = set()
        rows: list[ExtremeSustainedDPSRuntimeStateChoice] = []

        for choice in choices:
            key = choice.runtime_state_id
            if key in seen:
                unresolved.append(f"Duplicate runtime-state identity: {key}")
                continue
            seen.add(key)
            rows.append(choice)
            unresolved.extend(
                f"{key}: {item}"
                for item in choice.unresolved
            )

        if not rows:
            unresolved.append("Finite runtime-state family is empty")
        if not denominator_proven:
            unresolved.append(
                "Finite runtime-state denominator is not externally proven complete"
            )

        deduped = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        omitted = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in omitted_scope
                if str(item).strip()
            )
        )
        complete = bool(rows and denominator_proven and not deduped)

        return ExtremeSustainedDPSRuntimeStateFrontier(
            choices=tuple(rows),
            candidate_count=len(rows),
            denominator_proven=complete,
            evidence=(
                f"Finite runtime-state choices retained: {len(rows)}",
                f"Runtime-state denominator source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Canonical runtime_state axis denominator is locally proven"
                    if complete
                    else "Canonical runtime_state axis denominator remains open"
                ),
                "This service validates supplied runtime states; it does not invent proc/cooldown/condition timelines",
            ),
            unresolved=deduped,
            omitted_scope=omitted,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeStateChoice",
    "ExtremeSustainedDPSRuntimeStateFrontier",
    "ExtremeSustainedDPSRuntimeStateFrontierService",
]
