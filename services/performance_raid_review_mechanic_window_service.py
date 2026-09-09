from __future__ import annotations

"""Attribute observed raid failures to reviewed encounter windows.

Window identity is semantic. Numeric ESO ability IDs may be used upstream as raw
evidence to resolve a window, but they do not belong in ``semantic_key`` here.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_service import (
    RaidReviewFinding,
    RaidReviewObservation,
)


@dataclass(frozen=True, slots=True)
class RaidReviewEncounterWindow:
    report_code: str
    fight_id: int
    semantic_key: str
    label: str
    start_seconds: float
    end_seconds: float
    evidence_source: str = ""
    reviewed: bool = True

    @property
    def pull_key(self) -> tuple[str, int]:
        return (self.report_code, int(self.fight_id))

    @property
    def duration_seconds(self) -> float:
        return max(0.0, float(self.end_seconds) - float(self.start_seconds))

    def contains(self, timestamp_seconds: float) -> bool:
        timestamp = float(timestamp_seconds)
        return float(self.start_seconds) <= timestamp <= float(self.end_seconds)


class PerformanceRaidReviewMechanicWindowService:
    """Turn repeated death/window overlap into evidence-backed coaching findings."""

    def findings(
        self,
        observations: Iterable[RaidReviewObservation],
        windows: Iterable[RaidReviewEncounterWindow],
    ) -> tuple[RaidReviewFinding, ...]:
        rows = tuple(observations)
        reviewed_windows = tuple(window for window in windows if window.reviewed)
        if not rows or not reviewed_windows:
            return ()

        for window in reviewed_windows:
            if not window.semantic_key.strip():
                raise ValueError("Reviewed raid-review windows require a semantic_key.")
            if float(window.end_seconds) < float(window.start_seconds):
                raise ValueError(
                    f"Encounter window {window.semantic_key!r} ends before it starts."
                )

        by_pull: dict[tuple[str, int], list[RaidReviewObservation]] = {}
        for row in rows:
            if row.kill:
                continue
            by_pull.setdefault((row.report_code, int(row.fight_id)), []).append(row)

        windows_by_pull: dict[tuple[str, int], list[RaidReviewEncounterWindow]] = {}
        for window in reviewed_windows:
            windows_by_pull.setdefault(window.pull_key, []).append(window)

        measured_pull_count = 0
        earliest_matches: dict[str, list[RaidReviewEncounterWindow]] = {}
        player_matches: dict[tuple[str, str], list[RaidReviewEncounterWindow]] = {}

        for pull_key, pull_rows in by_pull.items():
            candidates = [
                row
                for row in pull_rows
                if row.death_count > 0 and row.first_death_seconds is not None
            ]
            if not candidates:
                continue
            earliest = min(candidates, key=lambda row: float(row.first_death_seconds or 0.0))
            pull_windows = windows_by_pull.get(pull_key, ())
            matching = [
                window
                for window in pull_windows
                if window.contains(float(earliest.first_death_seconds or 0.0))
            ]
            if not matching:
                continue
            measured_pull_count += 1
            selected = min(
                matching,
                key=lambda window: (window.duration_seconds, window.semantic_key),
            )
            earliest_matches.setdefault(selected.semantic_key, []).append(selected)

            for row in candidates:
                matching_player_windows = [
                    window
                    for window in pull_windows
                    if window.contains(float(row.first_death_seconds or 0.0))
                ]
                if not matching_player_windows:
                    continue
                player_window = min(
                    matching_player_windows,
                    key=lambda window: (window.duration_seconds, window.semantic_key),
                )
                player_matches.setdefault(
                    (row.stable_member_key, player_window.semantic_key), []
                ).append(player_window)

        findings: list[RaidReviewFinding] = []
        if measured_pull_count >= 2:
            for semantic_key, matched in earliest_matches.items():
                if len(matched) < 2:
                    continue
                share = len(matched) / measured_pull_count
                if share < 0.5:
                    continue
                label = matched[0].label or semantic_key
                findings.append(
                    RaidReviewFinding(
                        scope="raid",
                        subject="Raid",
                        role="Group",
                        category="mechanic_window",
                        priority="high" if share >= 0.75 else "medium",
                        title=f"First deaths repeatedly land in {label}",
                        evidence=(
                            f"The earliest observed death fell inside {label} in "
                            f"{len(matched)}/{measured_pull_count} measured wipe pulls "
                            f"({share * 100:.0f}%)."
                        ),
                        recommendation=(
                            f"Review execution during {label}: positioning, assigned mechanics, incoming damage, "
                            "support coverage, mitigation, and target handling. The window association is observed; "
                            "it is not by itself proof of which player or role caused the failure."
                        ),
                        confidence="high" if len(matched) >= 4 else "medium",
                    )
                )

        rows_by_member = {row.stable_member_key: row for row in rows}
        for (member_key, semantic_key), matched in player_matches.items():
            if len(matched) < 2:
                continue
            row = rows_by_member.get(member_key)
            if row is None:
                continue
            label = matched[0].label or semantic_key
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=row.actor_label,
                    role=row.canonical_role,
                    category="mechanic_window",
                    priority="medium",
                    title=f"Repeated deaths occur during {label}",
                    evidence=f"First death occurred inside {label} on {len(matched)} observed pulls.",
                    recommendation=(
                        f"Inspect this player's execution and required support during {label} before changing "
                        "their build or base rotation."
                    ),
                    confidence="medium",
                )
            )

        return tuple(findings)


__all__ = [
    "PerformanceRaidReviewMechanicWindowService",
    "RaidReviewEncounterWindow",
]
