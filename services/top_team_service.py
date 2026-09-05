from __future__ import annotations

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.esologs_client import (
    MUNDUS_STONE_NAMES,
    EsoLogsApiError,
    EsoLogsClient,
)
_MUNDUS_UPTIME_THRESHOLD_PERCENT = 60.0
_RANKED_TEAM_CANDIDATE_LIMIT = 10


class TopTeamService:
    """Read the current top encounter log as reusable observed build evidence.

    The initial fetch stays intentionally bounded: one ranking lookup, the fight,
    and one playerDetails payload. Class, gear-set names, and observed abilities are
    parsed from that payload. Mundus remains lazy because ESO Logs exposes it only as
    aura uptime; fetching it eagerly would add up to one network call per raid member.
    """

    def __init__(self, client: EsoLogsClient):
        self.client = client

    def list_trials(self) -> list[dict]:
        """Use the client's verified trial-only zone filter.

        ``EsoLogsClient.get_trial_zones`` owns the live zone IDs and the explicit
        trial-name allowlist. Keeping that boundary here prevents dungeons/arenas
        returned by ``worldData.zones`` from leaking into the Performance picker.
        """

        return self.client.get_trial_zones()

    def get_top_team(
        self,
        *,
        zone_id: int,
        zone_name: str,
        encounter_id: int,
        encounter_name: str,
    ) -> TopTeamResult:
        del zone_id  # retained in the public call shape for the trial picker.

        candidates = self.client.get_top_reports_for_encounter(
            int(encounter_id),
            limit=_RANKED_TEAM_CANDIDATE_LIMIT,
        )
        candidate_errors: list[str] = []
        for report_code, fight_id in candidates:
            try:
                fight = self.client.get_fight(report_code, fight_id)
                start = float(fight.get("startTime", 0))
                end = float(fight.get("endTime", 0))
                details = self.client.get_report_player_summary(
                    report_code,
                    fight_id,
                    start,
                    end,
                )
            except EsoLogsApiError as exc:
                candidate_errors.append(f"{report_code}#{fight_id}: {exc}")
                continue

            players = self._players_from_details(details)
            if players:
                return TopTeamResult(
                    TrialName=zone_name,
                    EncounterName=encounter_name,
                    ReportCode=report_code,
                    FightId=fight_id,
                    Players=players,
                )

            candidate_errors.append(
                f"{report_code}#{fight_id}: summary exposed no team players"
            )

        reason = "; ".join(candidate_errors) or "no usable ranked reports"
        raise EsoLogsApiError(
            f"Could not load a coordinated ranked team for {encounter_name}: {reason}."
        )

    @classmethod
    def _players_from_details(cls, details: dict) -> list[TopTeamPlayer]:
        players: list[TopTeamPlayer] = []
        for bucket, role in (("tanks", "tank"), ("healers", "healer"), ("dps", "dps")):
            for actor in details.get(bucket) or []:
                if not isinstance(actor, dict):
                    continue
                actor_id = actor.get("id")
                try:
                    normalized_actor_id = None if actor_id is None else int(actor_id)
                except (TypeError, ValueError):
                    normalized_actor_id = None
                players.append(
                    TopTeamPlayer(
                        Name=str(actor.get("name") or actor.get("displayName") or "Unknown"),
                        Role=role,
                        GearSets=cls._gear_sets(actor),
                        ClassName=cls._class_name(actor),
                        Abilities=cls._abilities(actor),
                        Mundus="",
                        ActorId=normalized_actor_id,
                    )
                )

        return players

    def get_player_mundus(
        self,
        *,
        report_code: str,
        fight_id: int,
        actor_id: int,
    ) -> str:
        """Resolve one player's Mundus on demand from buff uptime evidence."""

        fight = self.client.get_fight(report_code, fight_id)
        start = float(fight.get("startTime", 0.0))
        end = float(fight.get("endTime", 0.0))
        duration_ms = max(0.0, end - start)
        if duration_ms <= 0:
            return ""

        auras = self.client.get_aura_table(
            report_code,
            fight_id,
            start,
            end,
            data_type="Buffs",
            hostility_type="Friendlies",
            source_id=int(actor_id),
        )
        for aura in auras:
            if not isinstance(aura, dict):
                continue
            name = str(aura.get("name", "") or "").strip()
            if name not in MUNDUS_STONE_NAMES:
                continue
            try:
                uptime_ms = float(aura.get("totalUptime", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if (uptime_ms / duration_ms) * 100.0 >= _MUNDUS_UPTIME_THRESHOLD_PERCENT:
                return name
        return ""

    def resolve_player_mundus(
        self,
        result: TopTeamResult,
        player: TopTeamPlayer,
    ) -> str:
        """Convenience boundary for a future View/Add Template UI action."""

        if player.Mundus:
            return player.Mundus
        if player.ActorId is None or not result.ReportCode or not result.FightId:
            return ""
        return self.get_player_mundus(
            report_code=result.ReportCode,
            fight_id=result.FightId,
            actor_id=player.ActorId,
        )

    @staticmethod
    def _combatant_info(actor: dict) -> dict:
        info = actor.get("combatantInfo")
        return info if isinstance(info, dict) else actor

    @classmethod
    def _class_name(cls, actor: dict) -> str:
        info = cls._combatant_info(actor)
        return str(
            actor.get("type")
            or actor.get("class")
            or actor.get("className")
            or info.get("type")
            or info.get("class")
            or ""
        ).strip()

    @classmethod
    def _abilities(cls, actor: dict) -> list[str]:
        info = cls._combatant_info(actor)
        talents = info.get("talents")
        if not isinstance(talents, list):
            talents = actor.get("talents") if isinstance(actor.get("talents"), list) else []

        names: list[str] = []
        seen: set[str] = set()
        for talent in talents:
            if isinstance(talent, dict):
                nested = talent.get("ability")
                name = talent.get("name") or talent.get("displayName")
                if not name and isinstance(nested, dict):
                    name = nested.get("name")
            else:
                name = talent
            text = str(name or "").strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                names.append(text)
        return names

    @classmethod
    def _gear_sets(cls, actor: dict) -> list[str]:
        combatant = cls._combatant_info(actor)
        gear = combatant.get("gear") if isinstance(combatant, dict) else None
        if not isinstance(gear, list):
            gear = actor.get("gear") if isinstance(actor.get("gear"), list) else []

        names: list[str] = []
        seen: set[str] = set()
        for item in gear:
            if not isinstance(item, dict):
                continue
            nested_set = item.get("set")
            name = item.get("setName") or item.get("set_name")
            if not name and isinstance(nested_set, dict):
                name = nested_set.get("name")
            elif not name and isinstance(nested_set, str):
                name = nested_set
            if not name:
                continue
            text = str(name).strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                names.append(text)
        return names
