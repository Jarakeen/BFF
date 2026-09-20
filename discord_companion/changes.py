from __future__ import annotations

"""Detect player-facing Raid Plan build/assignment changes without owning plan state."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from discord_companion.config import DiscordCompanionConfig
from services.discord_companion_service import FoundryDockDiscordCompanionService
from services.paths import USER_DATA


DEFAULT_STATE_PATH = USER_DATA / "discord_companion_build_state.json"


@dataclass(frozen=True, slots=True)
class BuildChangeNotice:
    key: str
    channel_id: int
    plan_name: str
    player: str
    message: str


class BuildChangeMonitor:
    def __init__(
        self,
        *,
        companion: FoundryDockDiscordCompanionService,
        config: DiscordCompanionConfig,
        state_path: Path = DEFAULT_STATE_PATH,
    ) -> None:
        self.companion = companion
        self.config = config
        self.state_path = Path(state_path)
        self._state = self._load()

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        rows = payload.get("rows", {}) if isinstance(payload, dict) else {}
        return rows if isinstance(rows, dict) else {}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "rows": self._state}
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.state_path)

    @staticmethod
    def _fingerprint(payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _summary(payload: dict) -> str:
        pieces: list[str] = []
        build_name = str(payload.get("build") or "").strip()
        gear = tuple(payload.get("gear_sets") or ())
        skills = tuple(payload.get("skills") or ())
        assignments = tuple(payload.get("assignments") or ())
        if build_name:
            pieces.append(f"Build: {build_name}")
        elif gear:
            pieces.append("Gear: " + " + ".join(gear))
        if skills:
            pieces.append("Skills: " + ", ".join(skills))
        if assignments:
            pieces.append("Assignments: " + ", ".join(assignments))
        return "\n".join(pieces) or "The saved Raid Plan configuration changed."

    def scan(self) -> tuple[BuildChangeNotice, ...]:
        notices: list[BuildChangeNotice] = []
        dirty = False

        for plan in self.companion.list_plans():
            if plan.status == "archived" or not plan.team_name:
                continue
            channel_id = self.config.channel_id_for_team(plan.team_name)
            if channel_id is None:
                continue

            for member in plan.members:
                if not member.gamertag:
                    continue
                try:
                    brief = self.companion.build_brief(
                        plan_ref=plan.plan_id,
                        player_ref=member.seat_id,
                    )
                except LookupError:
                    continue
                payload = {
                    "build": brief.build,
                    "gear_sets": list(brief.gear_sets),
                    "skills": list(brief.skills),
                    "mundus": brief.mundus,
                    "assignments": list(brief.assignments),
                    "notes": brief.notes,
                }
                fingerprint = self._fingerprint(payload)
                key = f"{plan.plan_id}|{member.seat_id}"
                previous = self._state.get(key)
                if previous is None:
                    self._state[key] = {
                        "fingerprint": fingerprint,
                        "plan_name": plan.name,
                        "player": brief.player,
                    }
                    dirty = True
                    continue
                if previous.get("fingerprint") == fingerprint:
                    continue

                self._state[key] = {
                    "fingerprint": fingerprint,
                    "plan_name": plan.name,
                    "player": brief.player,
                }
                dirty = True
                notices.append(
                    BuildChangeNotice(
                        key=key,
                        channel_id=channel_id,
                        plan_name=plan.name,
                        player=brief.player,
                        message=(
                            f"**FoundryDock build update · {brief.player}**\n"
                            f"{plan.name} · {brief.seat_id}\n"
                            f"{self._summary(payload)}\n"
                            "Use /build for the full current brief."
                        ),
                    )
                )

        if dirty:
            self._save()
        return tuple(notices)


__all__ = ["BuildChangeMonitor", "BuildChangeNotice", "DEFAULT_STATE_PATH"]
