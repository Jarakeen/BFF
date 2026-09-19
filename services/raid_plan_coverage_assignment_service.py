from __future__ import annotations

"""Reconcile explicit Raid Plan effect ownership with Coverage evidence.

Assignments remain raid-lead intent. This service answers the narrower question Coverage
actually needs: does the explicitly assigned provider have static or conditional evidence
for the effect, is ownership duplicated, or is the effect still an unassigned gap?
"""

from dataclasses import dataclass

from services.raid_plan_coverage_scope_service import RaidPlanCoverageScope


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


def _evidence_owner(value: object) -> str:
    text = _clean(value)
    marker = " [planned:"
    index = text.casefold().find(marker)
    return text[:index].strip() if index >= 0 else text


@dataclass(frozen=True)
class RaidPlanCoverageAssignmentReview:
    effect_name: str
    primary: tuple[str, ...]
    backup: tuple[str, ...]
    supported_primary: tuple[str, ...]
    conditional_primary: tuple[str, ...]
    unsupported_primary: tuple[str, ...]
    supported_backup: tuple[str, ...]
    conditional_backup: tuple[str, ...]
    duplicate_primary: bool
    state: str
    label: str

    @property
    def coverage_state(self) -> str:
        """Raid-planning answer: covered or missing, independent of proof strength."""
        return "covered" if self.state != "gap" else "missing"

    @property
    def counts_as_planned_coverage(self) -> bool:
        """Planning presence is broader than static/runtime proof."""
        return self.coverage_state == "covered"

    @property
    def needs_attention(self) -> bool:
        # Attention means the plan deserves explanation/review, not that the effect is
        # absent. Assigned/conditional/unproven effects can still count as planned.
        return self.state in {
            "assigned_unproven",
            "backup_only",
            "unassigned_available",
        } or self.duplicate_primary


class RaidPlanCoverageAssignmentService:
    """Check explicit assignment ownership before Coverage considers generic providers."""

    @staticmethod
    def _provider_aliases(scope: RaidPlanCoverageScope) -> dict[str, set[str]]:
        aliases: dict[str, set[str]] = {}

        def add(owner: str, *values: object) -> None:
            owner_key = _key(owner)
            if not owner_key:
                return
            bucket = aliases.setdefault(owner_key, {owner_key})
            for value in values:
                value_key = _key(value)
                if value_key:
                    bucket.add(value_key)

        for row in scope.members:
            build = row.build
            add(
                row.player_label,
                getattr(build, "Name", ""),
                getattr(build, "Gamertag", ""),
                getattr(build, "BuildName", ""),
            )
        for row in scope.planned_gear:
            add(row.player_label)
        return aliases

    @classmethod
    def _matching_assignments(
        cls,
        scope: RaidPlanCoverageScope,
        assigned: tuple[str, ...],
        evidence: list[str],
    ) -> tuple[str, ...]:
        aliases = cls._provider_aliases(scope)
        evidence_keys = {_key(_evidence_owner(value)) for value in evidence if _clean(value)}
        matched: list[str] = []
        for provider in assigned:
            provider_key = _key(provider)
            provider_aliases = aliases.get(provider_key, {provider_key})
            if provider_aliases & evidence_keys:
                matched.append(provider)
        return tuple(matched)

    def review(self, *, effect_name: str, scope: RaidPlanCoverageScope, snapshot) -> RaidPlanCoverageAssignmentReview:
        primary = tuple(scope.primary_for(effect_name))
        backup = tuple(scope.secondary_for(effect_name))
        static_evidence = list(snapshot.providers.get(effect_name, ()) or ())
        conditional_evidence = list(snapshot.conditional_providers.get(effect_name, ()) or ())

        supported_primary = self._matching_assignments(scope, primary, static_evidence)
        conditional_primary = tuple(
            provider
            for provider in self._matching_assignments(scope, primary, conditional_evidence)
            if provider not in supported_primary
        )
        unsupported_primary = tuple(
            provider
            for provider in primary
            if provider not in supported_primary and provider not in conditional_primary
        )
        supported_backup = self._matching_assignments(scope, backup, static_evidence)
        conditional_backup = tuple(
            provider
            for provider in self._matching_assignments(scope, backup, conditional_evidence)
            if provider not in supported_backup
        )

        duplicate_primary = len(primary) > 1
        any_evidence = bool(static_evidence or conditional_evidence)

        if supported_primary:
            state = "assigned_supported"
            label = "Covered • Supported"
        elif conditional_primary:
            state = "assigned_conditional"
            label = "Covered • Conditional"
        elif primary:
            state = "assigned_unproven"
            label = "Covered • Planned"
        elif supported_backup or conditional_backup:
            state = "backup_only"
            label = "Covered • Backup only"
        elif any_evidence:
            state = "unassigned_available"
            label = "Covered • Unassigned"
        else:
            state = "gap"
            label = "Missing • No provider"

        if duplicate_primary:
            label += " • Duplicate primary"

        return RaidPlanCoverageAssignmentReview(
            effect_name=_clean(effect_name),
            primary=primary,
            backup=backup,
            supported_primary=supported_primary,
            conditional_primary=conditional_primary,
            unsupported_primary=unsupported_primary,
            supported_backup=supported_backup,
            conditional_backup=conditional_backup,
            duplicate_primary=duplicate_primary,
            state=state,
            label=label,
        )


__all__ = [
    "RaidPlanCoverageAssignmentReview",
    "RaidPlanCoverageAssignmentService",
]
