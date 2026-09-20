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

    def _request_json(self, path: str) -> dict:
        request = Request(
            self.base_url + path,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "FoundryDock/FinchClient",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 401:
                raise FinchApiError("Finch rejected the API key.") from exc
            if exc.code == 503:
                raise FinchApiError("Finch API authentication is not configured on the server.") from exc
            raise FinchApiError(f"Finch API returned HTTP {exc.code}.") from exc
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise FinchApiError(f"Could not reach Finch: {reason}") from exc
        except TimeoutError as exc:
            raise FinchApiError("Finch connection timed out.") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FinchApiError("Finch returned an invalid response.") from exc
        if not isinstance(payload, dict):
            raise FinchApiError("Finch returned an unexpected response.")
        return payload

    def test_connection(self) -> FinchConnectionStatus:
        payload = self._request_json("/api/v1/status")
        return FinchConnectionStatus(
            ok=bool(payload.get("ok")),
            service=str(payload.get("service") or ""),
            api_version=str(payload.get("api_version") or ""),
            discord_ready=bool(payload.get("discord_ready")),
            discord_user=str(payload.get("discord_user") or ""),
            database_ready=bool(payload.get("database_ready")),
        )


__all__ = ["FinchApiClient", "FinchApiError", "FinchConnectionStatus"]
