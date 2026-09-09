from __future__ import annotations

"""Cross-pull raid review analysis for the Performance Dashboard.

The existing performance dashboard is intentionally actor/fight focused.  This
module sits one layer above those snapshots: it compares repeated observations
from the same encounter and turns stable differences into coaching-oriented,
evidence-backed findings.

Important boundaries:
- Descriptive evidence comes first; recommendations never invent missing mechanics.
- Healing throughput is not treated as "higher is better" by itself.
- DD output comparisons use boss-active rate when available so immune/airborne
  downtime does not masquerade as a rotation problem.
- A finding always states the evidence that caused it to exist.
"""

from dataclasses import dataclass, field
from statistics import median
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RaidReviewObservation:
    report_code: str
    fight_id: int
    fight_name: str
    kill: bool
    actor_id: int
    actor_label: str
    role: str
    fight_duration_seconds: float
    output_total: float = 0.0
    output_per_second: float = 0.0
    boss_active_seconds: float | None = None
    death_count: int = 0
    first_death_seconds: float | None = None
    first_death_ability: str = ""
    minimum_primary_resource_percent: float | None = None
    key_uptimes: dict[str, float] = field(default_factory=dict)

    @property
    def encounter_key(self) -> str:
        return self.fight_name.strip().casefold()

    @property
    def canonical_role(self) -> str:
        raw = self.role.strip().casefold()
        if raw in {"healer", "healing"}:
            return "Healer"
        if raw in {"tank", "tanking"}:
            return "Tank"
        return "DPS"

    @property
    def active_output_per_second(self) -> float:
        active = self.boss_active_seconds
        if active is not None and active > 0 and self.output_total > 0:
            return self.output_total / active
        return max(0.0, self.output_per_second)


@dataclass(frozen=True, slots=True)
class RaidReviewFinding:
    scope: str  # player | role | raid
    subject: str
    role: str
    category: str
    priority: str  # high | medium | note
    title: str
    evidence: str
    recommendation: str
    confidence: str  # high | medium | low


@dataclass(frozen=True, slots=True)
class RaidReviewReport:
    encounter_name: str
    pull_count: int
    kill_count: int
    wipe_count: int
    findings: tuple[RaidReviewFinding, ...]


class PerformanceRaidReviewService:
    """Compare repeated encounter observations without turning logs into a scoreboard."""

    def analyze(
        self,
        observations: Iterable[RaidReviewObservation],
        *,
        encounter_name: str | None = None,
    ) -> RaidReviewReport:
        rows = tuple(observations)
        if not rows:
            return RaidReviewReport(
                encounter_name=encounter_name or "",
                pull_count=0,
                kill_count=0,
                wipe_count=0,
                findings=(),
            )

        encounter_key = (encounter_name or rows[0].fight_name).strip().casefold()
        rows = tuple(row for row in rows if row.encounter_key == encounter_key)
        if not rows:
            return RaidReviewReport(
                encounter_name=encounter_name or "",
                pull_count=0,
                kill_count=0,
                wipe_count=0,
                findings=(),
            )

        pull_keys = {(row.report_code, row.fight_id) for row in rows}
        kill_keys = {
            (row.report_code, row.fight_id)
            for row in rows
            if row.kill
        }
        wipe_keys = pull_keys - kill_keys

        findings: list[RaidReviewFinding] = []
        findings.extend(self._repeated_player_deaths(rows))
        findings.extend(self._dd_kill_wipe_output(rows))
        findings.extend(self._support_resource_pressure(rows))
        findings.extend(self._uptime_consistency(rows))

        priority_order = {"high": 0, "medium": 1, "note": 2}
        findings.sort(
            key=lambda item: (
                priority_order.get(item.priority, 9),
                item.scope,
                item.subject.casefold(),
                item.category,
            )
        )

        return RaidReviewReport(
            encounter_name=rows[0].fight_name,
            pull_count=len(pull_keys),
            kill_count=len(kill_keys),
            wipe_count=len(wipe_keys),
            findings=tuple(findings),
        )

    @staticmethod
    def _by_player(rows: tuple[RaidReviewObservation, ...]) -> dict[tuple[int, str], list[RaidReviewObservation]]:
        grouped: dict[tuple[int, str], list[RaidReviewObservation]] = {}
        for row in rows:
            grouped.setdefault((row.actor_id, row.actor_label), []).append(row)
        return grouped

    def _repeated_player_deaths(
        self,
        rows: tuple[RaidReviewObservation, ...],
    ) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for (_, label), player_rows in self._by_player(rows).items():
            wipes = [row for row in player_rows if not row.kill]
            if len(wipes) < 2:
                continue
            death_wipes = [row for row in wipes if row.death_count > 0]
            if len(death_wipes) < 2:
                continue

            share = len(death_wipes) / len(wipes)
            if share < 0.5:
                continue

            causes = [row.first_death_ability.strip() for row in death_wipes if row.first_death_ability.strip()]
            cause_note = ""
            if causes:
                counts: dict[str, int] = {}
                for cause in causes:
                    counts[cause] = counts.get(cause, 0) + 1
                cause, count = max(counts.items(), key=lambda item: (item[1], item[0]))
                if count >= 2:
                    cause_note = f" Most common first-death cause: {cause} ({count} pulls)."

            role = player_rows[0].canonical_role
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=label,
                    role=role,
                    category="survival",
                    priority="high" if share >= 0.75 else "medium",
                    title="Repeated deaths are appearing in wipes",
                    evidence=(
                        f"Died in {len(death_wipes)}/{len(wipes)} observed wipes "
                        f"({share * 100:.0f}%).{cause_note}"
                    ),
                    recommendation=(
                        "Review the repeated death windows before changing throughput. "
                        "Check mechanic handling, positioning, mitigation, and whether required support coverage was already active."
                    ),
                    confidence="high" if len(wipes) >= 4 else "medium",
                )
            )
        return findings

    def _dd_kill_wipe_output(
        self,
        rows: tuple[RaidReviewObservation, ...],
    ) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for (_, label), player_rows in self._by_player(rows).items():
            if player_rows[0].canonical_role != "DPS":
                continue
            kills = [row.active_output_per_second for row in player_rows if row.kill and row.active_output_per_second > 0]
            wipes = [row.active_output_per_second for row in player_rows if not row.kill and row.active_output_per_second > 0]
            if len(kills) < 2 or len(wipes) < 2:
                continue

            kill_median = median(kills)
            wipe_median = median(wipes)
            if kill_median <= 0:
                continue
            delta = (wipe_median - kill_median) / kill_median
            if abs(delta) < 0.12:
                continue

            if delta < 0:
                title = "Damage falls meaningfully on wipe pulls"
                recommendation = (
                    "Inspect movement, target reacquisition, deaths, mechanic assignments, and burst alignment in the lower-output pulls. "
                    "Do not assume the rotation itself is the cause until those windows are checked."
                )
            else:
                title = "Raw damage is not the wipe signal"
                recommendation = (
                    "Wipe pulls are not showing a damage-rate deficit for this player. "
                    "Prioritize survival, mechanics, target choice, and group timing before asking for more raw DPS."
                )

            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=label,
                    role="DPS",
                    category="damage",
                    priority="medium" if delta < 0 else "note",
                    title=title,
                    evidence=(
                        f"Median boss-active output: kills {kill_median:,.0f}/s vs wipes {wipe_median:,.0f}/s "
                        f"({delta * 100:+.0f}%)."
                    ),
                    recommendation=recommendation,
                    confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                )
            )
        return findings

    def _support_resource_pressure(
        self,
        rows: tuple[RaidReviewObservation, ...],
    ) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for (_, label), player_rows in self._by_player(rows).items():
            role = player_rows[0].canonical_role
            if role not in {"Healer", "Tank"}:
                continue
            measured = [
                row for row in player_rows
                if row.minimum_primary_resource_percent is not None
            ]
            if len(measured) < 3:
                continue
            pressured = [
                row for row in measured
                if float(row.minimum_primary_resource_percent or 0.0) <= 15.0
            ]
            if len(pressured) < 2:
                continue

            wipe_pressure = sum(1 for row in pressured if not row.kill)
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=label,
                    role=role,
                    category="sustain",
                    priority="medium",
                    title="Repeated resource pressure deserves review",
                    evidence=(
                        f"Primary resource reached 15% or lower in {len(pressured)}/{len(measured)} measured pulls; "
                        f"{wipe_pressure} of those were wipes."
                    ),
                    recommendation=(
                        "Inspect the exact low-resource windows and preceding cast/block cadence. "
                        "Treat this as a timing/sustain question, not proof that the build needs more recovery."
                    ),
                    confidence="medium",
                )
            )
        return findings

    def _uptime_consistency(
        self,
        rows: tuple[RaidReviewObservation, ...],
    ) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for (_, label), player_rows in self._by_player(rows).items():
            effect_names = sorted(
                {
                    name
                    for row in player_rows
                    for name in row.key_uptimes
                    if name.strip()
                },
                key=str.casefold,
            )
            for effect_name in effect_names:
                kills = [
                    row.key_uptimes[effect_name]
                    for row in player_rows
                    if row.kill and effect_name in row.key_uptimes
                ]
                wipes = [
                    row.key_uptimes[effect_name]
                    for row in player_rows
                    if not row.kill and effect_name in row.key_uptimes
                ]
                if len(kills) < 2 or len(wipes) < 2:
                    continue
                kill_median = median(kills)
                wipe_median = median(wipes)
                delta = wipe_median - kill_median
                if abs(delta) < 10.0:
                    continue

                role = player_rows[0].canonical_role
                direction = "lower" if delta < 0 else "higher"
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=label,
                        role=role,
                        category="uptime",
                        priority="medium" if delta < 0 else "note",
                        title=f"{effect_name} uptime is {direction} on wipes",
                        evidence=(
                            f"Median uptime: kills {kill_median:.1f}% vs wipes {wipe_median:.1f}% "
                            f"({delta:+.1f} points)."
                        ),
                        recommendation=(
                            "Inspect whether the difference occurs during eligible encounter windows and whether this player owns the effect obligation. "
                            "Do not score impossible or unassigned uptime as a mistake."
                        ),
                        confidence="medium",
                    )
                )
        return findings


__all__ = [
    "PerformanceRaidReviewService",
    "RaidReviewFinding",
    "RaidReviewObservation",
    "RaidReviewReport",
]
