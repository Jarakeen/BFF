from __future__ import annotations

import time
from typing import Any

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.esologs_client import EsoLogsApiError, EsoLogsClient


# How many top individual parses to pull per role. These can (and
# often do) come from different reports/guilds -- that's the point:
# a broader, community-wide "what's trending" sample rather than one
# team's roster from a single pull.
_TOP_N_PER_ROLE = 5

# role bucket key -> (RoleType enum value, CharacterRankingMetricType
# enum value) for EsoLogsClient.get_role_rankings. Tank rankings
# don't have a natural "highest output" metric the way DPS/healers
# do -- "dps" is the conventional choice these platforms use for
# ranking tanks too (by their own damage output within the Tank
# role), but this is the least certain part of this feature; if ESO
# Logs rejects it or the results look wrong, this one line is what
# to change.
_ROLE_QUERY_PARAMS = {
    "tank": ("Tank", "dps"),
    "healer": ("Healer", "hps"),
    "dps": ("DPS", "dps"),
}

# A genuine transient 500 from ESO Logs' own server is worth one
# short retry before giving up on that specific call -- this is
# specifically for "Internal server error" text, not for other
# errors (auth, malformed query, etc.), which should surface
# immediately rather than being retried.
_MAX_QUERY_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 1.5


class TopTeamService:
    """
    Read the current top-ranked individual players for each role
    (Tank / Healer / DPS) on a boss and summarize their role, class,
    gear sets, and skills.

    Uses EsoLogsClient's own get_trial_zones / get_role_rankings /
    get_report_player_summary methods rather than a separate inline
    query set, so there is exactly one place that owns the GraphQL
    shape for "top ranked team" data.
    """

    def __init__(self, client: EsoLogsClient):
        self.client = client

    # --------------------------------------------------
    # Trial / boss picker data
    # --------------------------------------------------

    def list_trials(self) -> list[dict]:
        return self._call_with_retry(self.client.get_trial_zones)

    # --------------------------------------------------
    # Top players per role for a chosen trial + boss
    # --------------------------------------------------

    def get_top_team(
        self,
        *,
        zone_id: int,
        zone_name: str,
        encounter_id: int,
        encounter_name: str,
    ) -> TopTeamResult:

        del zone_id  # kept for call-site symmetry with list_trials()

        players: list[TopTeamPlayer] = []

        # Multiple top-ranked players (even across different roles)
        # can come from the very same log -- cache each unique
        # report+fight's gear-details fetch so that log only gets
        # queried once, no matter how many of its players rank in
        # the top N somewhere.
        details_cache: dict[tuple[str, int], dict | None] = {}

        seen_role_names: set[tuple[str, str]] = set()

        role_errors: list[str] = []

        for role_key, (role_enum, metric) in _ROLE_QUERY_PARAMS.items():

            try:
                entries = self._call_with_retry(
                    self.client.get_role_rankings,
                    encounter_id,
                    role_enum,
                    metric,
                    _TOP_N_PER_ROLE,
                )

            except EsoLogsApiError as exc:

                role_errors.append(f"{role_key}: {exc}")

                continue

            for entry in entries:

                name = str(entry.get("name") or "").strip()

                dedupe_key = (role_key, name.casefold())

                if not name or dedupe_key in seen_role_names:
                    continue

                key = (entry["report_code"], entry["fight_id"])

                if key not in details_cache:

                    details_cache[key] = self._fetch_details_or_none(
                        key[0], key[1], role_errors, role_key
                    )

                details = details_cache[key]

                if not details:
                    continue

                actor = self._find_actor(details, role_key, name)

                if actor is None:
                    continue

                seen_role_names.add(dedupe_key)

                players.append(
                    TopTeamPlayer(
                        Name=name,
                        Role=role_key,
                        ClassName=self._class_name(actor) or str(entry.get("class") or ""),
                        GearSets=self._gear_sets(actor),
                        Abilities=self._abilities(actor),
                    )
                )

        if not players:
            raise EsoLogsApiError(
                f"Could not build a top-players list for {encounter_name} "
                f"({'; '.join(role_errors) if role_errors else 'no ranked entries found'})."
            )

        unique_reports = {key for key, details in details_cache.items() if details}

        primary_report, primary_fight = (
            next(iter(unique_reports)) if unique_reports else ("", 0)
        )

        return TopTeamResult(
            TrialName=zone_name,
            EncounterName=encounter_name,
            ReportCode=primary_report,
            FightId=primary_fight,
            SourceReportCount=len(unique_reports),
            Players=players,
        )

    def _fetch_details_or_none(
        self,
        report_code: str,
        fight_id: int,
        role_errors: list[str],
        role_key: str,
    ) -> dict | None:

        try:

            fight = self._call_with_retry(self.client.get_fight, report_code, fight_id)

            start = float(fight.get("startTime", 0))
            end = float(fight.get("endTime", 0))

            return self._call_with_retry(
                self.client.get_report_player_summary,
                report_code,
                fight_id,
                start,
                end,
            )

        except EsoLogsApiError as exc:

            role_errors.append(f"{role_key} ({report_code}#{fight_id}): {exc}")

            return None

    @staticmethod
    def _find_actor(details: dict, role_key: str, name: str) -> dict | None:

        bucket_key = {"tank": "tanks", "healer": "healers", "dps": "dps"}[role_key]

        target = name.casefold()

        for actor in details.get(bucket_key) or []:

            if str(actor.get("name", "")).strip().casefold() == target:
                return actor

        return None

    # --------------------------------------------------
    # Resilience: retry a genuinely transient server error once
    # before giving up on that specific call.
    # --------------------------------------------------

    def _call_with_retry(self, fn, *args, **kwargs) -> Any:

        last_error: EsoLogsApiError | None = None

        for attempt in range(_MAX_QUERY_ATTEMPTS):

            try:
                return fn(*args, **kwargs)

            except EsoLogsApiError as exc:

                last_error = exc

                # Only a genuine server-side 500 is worth retrying the
                # exact same request -- anything else (auth, a bad
                # argument, a missing report) will fail identically
                # every time, so surface it immediately instead of
                # burning a retry on it.
                if "internal server error" not in str(exc).casefold():
                    raise

                if attempt + 1 < _MAX_QUERY_ATTEMPTS:
                    time.sleep(_RETRY_DELAY_SECONDS)

        raise last_error

    # --------------------------------------------------
    # playerDetails actor parsing
    # --------------------------------------------------

    @staticmethod
    def _class_name(actor: dict) -> str:
        # ESO Logs' playerDetails entries carry the class under
        # `type` (e.g. "Templar", "Warden") in every shape this API
        # has been observed to return it in; `class` is checked as a
        # defensive fallback in case that ever changes.
        name = actor.get("type") or actor.get("class") or ""
        return str(name).strip()

    @classmethod
    def _abilities(cls, actor: dict) -> list[str]:
        combatant = actor.get("combatantInfo") if isinstance(actor.get("combatantInfo"), dict) else actor
        talents = combatant.get("talents") if isinstance(combatant, dict) else None
        if not isinstance(talents, list):
            talents = actor.get("talents") if isinstance(actor.get("talents"), list) else []

        names: list[str] = []
        seen: set[str] = set()
        for talent in talents:
            if isinstance(talent, dict):
                name = talent.get("name") or talent.get("ability")
            elif isinstance(talent, str):
                name = talent
            else:
                continue
            if not name:
                continue
            text = str(name).strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                names.append(text)
        return names

    @classmethod
    def _gear_sets(cls, actor: dict) -> list[str]:
        combatant = actor.get("combatantInfo") if isinstance(actor.get("combatantInfo"), dict) else actor
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
