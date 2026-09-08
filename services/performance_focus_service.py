from __future__ import annotations

"""Performance-focus goals shared by Capabilities and the Operations overview.

The focus layer is intentionally conservative. ESO Logs build evidence may suggest
likely responsibilities, but it never silently assigns one. Only goals the user
pins (or creates manually) are persisted to Operations.
"""

from dataclasses import asdict, dataclass
import json
from math import ceil
from pathlib import Path

from services.top_team_service import TopTeamService


@dataclass(frozen=True)
class PerformanceBuildEvidence:
    ClassName: str = ""
    Role: str = ""
    GearSets: tuple[str, ...] = ()
    Abilities: tuple[str, ...] = ()


@dataclass
class PerformanceFocusGoal:
    Name: str
    TargetPercent: float
    CurrentPercent: float | None = None
    Source: str = "Custom"
    ReportCode: str = ""
    FightId: str = ""
    FightName: str = ""
    ActorLabel: str = ""
    Role: str = ""
    EvidenceNote: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PerformanceFocusGoal":
        return cls(
            Name=str(data.get("Name") or "").strip(),
            TargetPercent=float(data.get("TargetPercent") or 0.0),
            CurrentPercent=(
                None
                if data.get("CurrentPercent") is None
                else float(data.get("CurrentPercent"))
            ),
            Source=str(data.get("Source") or "Custom"),
            ReportCode=str(data.get("ReportCode") or ""),
            FightId=str(data.get("FightId") or ""),
            FightName=str(data.get("FightName") or ""),
            ActorLabel=str(data.get("ActorLabel") or ""),
            Role=str(data.get("Role") or ""),
            EvidenceNote=str(data.get("EvidenceNote") or ""),
        )


class PerformanceFocusStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> list[PerformanceFocusGoal]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        values = payload.get("Goals", []) if isinstance(payload, dict) else []
        return [
            PerformanceFocusGoal.from_dict(row)
            for row in values
            if isinstance(row, dict) and str(row.get("Name") or "").strip()
        ]

    def save(self, goals: list[PerformanceFocusGoal]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"Goals": [goal.to_dict() for goal in goals]}, indent=2),
            encoding="utf-8",
        )

    def upsert(self, goal: PerformanceFocusGoal) -> None:
        goals = self.load()
        key = goal.Name.casefold()
        replaced = False
        for index, existing in enumerate(goals):
            if existing.Name.casefold() == key:
                goals[index] = goal
                replaced = True
                break
        if not replaced:
            goals.append(goal)
        self.save(goals[:8])

    def remove(self, name: str) -> None:
        key = str(name or "").strip().casefold()
        self.save([goal for goal in self.load() if goal.Name.casefold() != key])


def suggest_working_target(current_percent: float) -> float:
    """Offer a modest next-step target, not an ESO authority claim."""
    current = max(0.0, min(100.0, float(current_percent)))
    return min(95.0, max(10.0, ceil(current / 5.0) * 5.0 + 10.0))


def fetch_player_build_evidence(
    client,
    *,
    report_code: str,
    fight_id: int,
    actor_id: int,
    start_ms: float,
    end_ms: float,
    role: str,
) -> PerformanceBuildEvidence:
    """Read one actor's combatantInfo from the report; fail-soft at the caller."""
    details = client.get_report_player_summary(
        report_code,
        int(fight_id),
        float(start_ms),
        float(end_ms),
    )
    for bucket in ("tanks", "healers", "dps"):
        for actor in details.get(bucket) or []:
            if not isinstance(actor, dict):
                continue
            try:
                found_id = int(actor.get("id"))
            except (TypeError, ValueError):
                continue
            if found_id != int(actor_id):
                continue
            return PerformanceBuildEvidence(
                ClassName=TopTeamService._class_name(actor),
                Role=str(role or bucket.rstrip("s")),
                GearSets=tuple(TopTeamService._gear_sets(actor)),
                Abilities=tuple(TopTeamService._abilities(actor)),
            )
    return PerformanceBuildEvidence(Role=str(role or ""))


def likely_responsibilities(evidence: PerformanceBuildEvidence) -> list[tuple[str, str]]:
    """Return high-confidence *suggestions*, never assignments.

    Suggestions require explicit class, gear, or ability evidence that strongly
    points to the effect source. Role context changes which clues are useful, but
    the UI still requires the user to pin a goal before it reaches Operations.
    """
    class_name = evidence.ClassName.casefold()
    role = evidence.Role.casefold()
    gear = {name.casefold() for name in evidence.GearSets}
    abilities = {name.casefold() for name in evidence.Abilities}
    suggestions: list[tuple[str, str]] = []

    def has_ability(*needles: str) -> bool:
        return any(
            any(needle.casefold() in ability for needle in needles)
            for ability in abilities
        )

    def add(name: str, note: str) -> None:
        if name.casefold() not in {current.casefold() for current, _ in suggestions}:
            suggestions.append((name, note))

    # Healer / support clues.
    if "warden" in class_name and "heal" in role:
        add("Major Mending", "Warden healer class context")
    if "spell power cure" in gear:
        add("Major Courage", "Spell Power Cure detected in ESO Logs gear")
    if "roaring opportunist" in gear:
        add("Major Slayer", "Roaring Opportunist detected in ESO Logs gear")
    if "turning tide" in gear or "archdruid devyric" in gear:
        add("Major Vulnerability", "Major Vulnerability set detected in ESO Logs gear")
    if has_ability("aggressive horn") or "war horn" in abilities:
        add("Major Force", "War Horn detected in ESO Logs abilities")
    if has_ability("combat prayer"):
        add("Minor Berserk", "Combat Prayer detected in ESO Logs abilities")

    # DPS clues. Received raid buffs are useful context, but they are not added as
    # personal goals unless the build itself shows a likely source.
    if "dps" in role:
        if has_ability("barbed trap", "channeled acceleration", "accelerate"):
            add("Minor Force", "Minor Force source detected in ESO Logs abilities")
        if any("kinras" in item for item in gear):
            add("Major Berserk", "Kinras gear detected in ESO Logs build evidence")

    # Tank clues. These are intentionally source-specific so a tank is not graded
    # on every possible raid debuff merely because tanks often carry them.
    if "tank" in role:
        if has_ability("pierce armor"):
            add("Major Breach", "Pierce Armor detected in ESO Logs abilities")
            add("Minor Breach", "Pierce Armor detected in ESO Logs abilities")
        elif has_ability("elemental susceptibility", "weakness to elements"):
            add("Major Breach", "Major Breach source detected in ESO Logs abilities")

        if has_ability(
            "hardened armor",
            "volatile armor",
            "ice fortress",
            "expansive frost cloak",
            "frost cloak",
            "boundless storm",
            "hurricane",
            "restoring focus",
            "channeled focus",
            "summoner's armor",
            "beckoning armor",
            "cruxweaver armor",
        ):
            add("Major Resolve", "Defensive armor buff detected in ESO Logs abilities")
        if has_ability("revealing flare"):
            add("Major Protection", "Revealing Flare detected in ESO Logs abilities")

    return suggestions
