from __future__ import annotations

"""Authenticated HTTP client for the hosted Finch companion API."""

from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class FinchConnectionStatus:
    ok: bool
    service: str = ""
    api_version: str = ""
    discord_ready: bool = False
    discord_user: str = ""
    database_ready: bool = False
    client: str = ""
    client_scopes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FinchGearNeedRequest:
    request_id: int
    discord_user_id: int
    guild_id: int
    team_name: str
    player_name: str
    gear_needed: str
    created_at: str = ""


class FinchApiError(RuntimeError):
    pass


class FinchApiClient:
    def __init__(self, *, base_url: str, api_key: str, timeout: float = 10.0) -> None:
        self.base_url = str(base_url or "").strip().rstrip("/")
        if self.base_url and "://" not in self.base_url:
            self.base_url = "https://" + self.base_url
        self.api_key = str(api_key or "").strip()
        self.timeout = float(timeout)
        if not self.base_url:
            raise FinchApiError("Finch API URL is required.")
        if not self.api_key:
            raise FinchApiError("Finch API key is required.")

    def _request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict | None = None,
    ) -> dict:
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "FoundryDock/FinchClient",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=str(method or "GET").upper(),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 401:
                raise FinchApiError("Finch rejected the API key.") from exc
            if exc.code == 403:
                raise FinchApiError("This Finch client is not permitted to perform that action.") from exc
            if exc.code == 503:
                raise FinchApiError("Finch API authentication is not configured on the server.") from exc
            raise FinchApiError(f"Finch API returned HTTP {exc.code}.") from exc
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise FinchApiError(f"Could not reach Finch: {reason}") from exc
        except TimeoutError as exc:
            raise FinchApiError("Finch connection timed out.") from exc

        try:
            payload_data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FinchApiError("Finch returned an invalid response.") from exc
        if not isinstance(payload_data, dict):
            raise FinchApiError("Finch returned an unexpected response.")
        return payload_data

    def test_connection(self) -> FinchConnectionStatus:
        payload = self._request_json("/api/v1/status")
        raw_scopes = payload.get("client_scopes")
        scopes = (
            tuple(str(value) for value in raw_scopes if str(value).strip())
            if isinstance(raw_scopes, list)
            else ()
        )
        return FinchConnectionStatus(
            ok=bool(payload.get("ok")),
            service=str(payload.get("service") or ""),
            api_version=str(payload.get("api_version") or ""),
            discord_ready=bool(payload.get("discord_ready")),
            discord_user=str(payload.get("discord_user") or ""),
            database_ready=bool(payload.get("database_ready")),
            client=str(payload.get("client") or ""),
            client_scopes=scopes,
        )

    def pending_gear_needs(self) -> tuple[FinchGearNeedRequest, ...]:
        payload = self._request_json("/api/v1/gear-needs/pending")
        rows = payload.get("requests")
        if not isinstance(rows, list):
            raise FinchApiError("Finch returned an invalid gear-needs response.")

        result: list[FinchGearNeedRequest] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                request_id = int(row.get("request_id"))
                discord_user_id = int(row.get("discord_user_id"))
                guild_id = int(row.get("guild_id"))
            except (TypeError, ValueError) as exc:
                raise FinchApiError("Finch returned a gear-needs row with invalid identity fields.") from exc
            result.append(
                FinchGearNeedRequest(
                    request_id=request_id,
                    discord_user_id=discord_user_id,
                    guild_id=guild_id,
                    team_name=str(row.get("team_name") or "").strip(),
                    player_name=str(row.get("player_name") or "").strip(),
                    gear_needed=str(row.get("gear_needed") or "").strip(),
                    created_at=str(row.get("created_at") or "").strip(),
                )
            )
        return tuple(result)

    def acknowledge_gear_need(
        self,
        request_id: int,
        *,
        status: str,
        message: str = "",
    ) -> None:
        state = str(status or "").strip().casefold()
        if state not in {"applied", "rejected"}:
            raise ValueError("Finch acknowledgement status must be 'applied' or 'rejected'.")
        self._request_json(
            f"/api/v1/gear-needs/{int(request_id)}/ack",
            method="POST",
            payload={
                "status": state,
                "message": str(message or "").strip(),
            },
        )


__all__ = [
    "FinchApiClient",
    "FinchApiError",
    "FinchConnectionStatus",
    "FinchGearNeedRequest",
]
