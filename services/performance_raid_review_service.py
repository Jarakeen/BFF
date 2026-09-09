from __future__ import annotations

"""Cross-pull, evidence-backed raid review analysis for Performance."""

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
    # Stable identity supplied by the caller when observations from multiple
    # reports belong to the same person. ESO Logs actor IDs are report-scoped.
    # If absent, grouping deliberately stays report-local.
    member_key: str = ""
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

    @property
    def stable_member_key(self) -> str:
        explicit = self.member_key.strip().casefold()
        if explicit:
            return explicit
        return f"{self.report_code.strip().casefold()}:{self.actor_id}"


@dataclass(frozen=True, slots=True)
class RaidReviewFinding:
    scope: str
    subject: str
    role: str
    category: str
    priority: str
    title: str
    evidence: str
    recommendation: str
    confidence: str


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
            return RaidReviewReport(encounter_name or "", 0, 0, 0, ())

        encounter_key = (encounter_name or rows[0].fight_name).strip().casefold()
        rows = tuple(row for row in rows if row.encounter_key == encounter_key)
        if not rows:
            return RaidReviewReport(encounter_name or "", 0, 0, 0, ())

        pull_keys = {(row.report_code, row.fight_id) for row in rows}
        kill_keys = {(row.report_code, row.fight_id) for row in rows if row.kill}
        wipe_keys = pull_keys - kill_keys

        findings: list[RaidReviewFinding] = []
        findings.extend(self._repeated_player_deaths(rows))
        findings.extend(self._dd_kill_wipe_output(rows))
        findings.extend(self._support_resource_pressure(rows))
        findings.extend(self._uptime_consistency(rows))

        order = {"high": 0, "medium": 1, "note": 2}
        findings.sort(
            key=lambda item: (
                order.get(item.priority, 9),
                item.scope,
                item.subject.casefold(),
                item.category,
            )
        )
        return RaidReviewReport(
            rows[0].fight_name,
            len(pull_keys),
            len(kill_keys),
            len(wipe_keys),
            tuple(findings),
        )

    @staticmethod
    def _by_player(
        rows: tuple[RaidReviewObservation, ...],
    ) -> dict[str, list[RaidReviewObservation]]:
        grouped: dict[str, list[RaidReviewObservation]] = {}
        for row in rows:
            grouped.setdefault(row.stable_member_key, []).append(row)
        return grouped

    def _repeated_player_deaths(self, rows) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for player_rows in self._by_player(rows).values():
            label = player_rows[0].actor_label
            wipes = [row for row in player_rows if not row.kill]
            death_wipes = [row for row in wipes if row.death_count > 0]
            if len(wipes) < 2 or len(death_wipes) < 2:
                continue
            share = len(death_wipes) / len(wipes)
            if share < 0.5:
                continue

            causes = [
                row.first_death_ability.strip()
                for row in death_wipes
                if row.first_death_ability.strip()
            ]
            cause_note = ""
            if causes:
                counts: dict[str, int] = {}
                for cause in causes:
                    counts[cause] = counts.get(cause, 0) + 1
                cause, count = max(counts.items(), key=lambda item: (item[1], item[0]))
                if count >= 2:
                    cause_note = f" Most common first-death cause: {cause} ({count} pulls)."

            findings.append(
                RaidReviewFinding(
                    "player",
                    label,
                    player_rows[0].canonical_role,
                    "survival",
                    "high" if share >= 0.75 else "medium",
                    "Repeated deaths are appearing in wipes",
                    f"Died in {len(death_wipes)}/{len(wipes)} observed wipes ({share * 100:.0f}%).{cause_note}",
                    "Review the repeated death windows before changing throughput. Check mechanic handling, positioning, mitigation, and whether required support coverage was already active.",
                    "high" if len(wipes) >= 4 else "medium",
                )
            )
        return findings

    def _dd_kill_wipe_output(self, rows) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for player_rows in self._by_player(rows).values():
            if player_rows[0].canonical_role != "DPS":
                continue
            label = player_rows[0].actor_label
            kills = [
                row.active_output_per_second
                for row in player_rows
                if row.kill and row.active_output_per_second > 0
            ]
            wipes = [
                row.active_output_per_second
                for row in player_rows
                if not row.kill and row.active_output_per_second > 0
            ]
            if len(kills) < 2 or len(wipes) < 2:
                continue
            kill_median = median(kills)
            wipe_median = median(wipes)
            if kill_median <= 0:
                continue
            delta = (wipe_median - kill_median) / kill_median
            if abs(delta) < 0.12:
                continue

            lower = delta < 0
            findings.append(
                RaidReviewFinding(
                    "player",
                    label,
                    "DPS",
                    "damage",
                    "medium" if lower else "note",
                    "Damage falls meaningfully on wipe pulls" if lower else "Raw damage is not the wipe signal",
                    f"Median boss-active output: kills {kill_median:,.0f}/s vs wipes {wipe_median:,.0f}/s ({delta * 100:+.0f}%).",
                    (
                        "Inspect movement, target reacquisition, deaths, mechanic assignments, and burst alignment in the lower-output pulls. Do not assume the rotation itself is the cause until those windows are checked."
                        if lower
                        else "Wipe pulls are not showing a damage-rate deficit for this player. Prioritize survival, mechanics, target choice, and group timing before asking for more raw DPS."
                    ),
                    "high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                )
            )
        return findings

    def _support_resource_pressure(self, rows) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for player_rows in self._by_player(rows).values():
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
                    "player",
                    player_rows[0].actor_label,
                    role,
                    "sustain",
                    "medium",
                    "Repeated resource pressure deserves review",
                    f"Primary resource reached 15% or lower in {len(pressured)}/{len(measured)} measured pulls; {wipe_pressure} of those were wipes.",
                    "Inspect the exact low-resource windows and preceding cast/block cadence. Treat this as a timing/sustain question, not proof that the build needs more recovery.",
                    "medium",
                )
            )
        return findings

    def _uptime_consistency(self, rows) -> list[RaidReviewFinding]:
        findings: list[RaidReviewFinding] = []
        for player_rows in self._by_player(rows).values():
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
                lower = delta < 0
                findings.append(
                    RaidReviewFinding(
                        "player",
                        player_rows[0].actor_label,
                        player_rows[0].canonical_role,
                        "uptime",
                        "medium" if lower else "note",
                        f"{effect_name} uptime is {'lower' if lower else 'higher'} on wipes",
                        f"Median uptime: kills {kill_median:.1f}% vs wipes {wipe_median:.1f}% ({delta:+.1f} points).",
                        "Inspect whether the difference occurs during eligible encounter windows and whether this player owns the effect obligation. Do not score impossible or unassigned uptime as a mistake.",
                        "medium",
                    )
                )
        return findings


__all__ = [
    "PerformanceRaidReviewService",
    "RaidReviewFinding",
    "RaidReviewObservation",
    "RaidReviewReport",
]
