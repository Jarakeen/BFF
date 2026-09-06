from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener


PAGE_URL = "https://eso-hub.com/en/scribing-simulator"
INITIALIZE_URL = "https://eso-hub.com/api/scribing-simulator/initialize"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)


def _request(url: str, *, referer: str | None = None, json_request: bool = False) -> Request:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    if json_request:
        headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
        )
    else:
        headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            }
        )
    return Request(url, headers=headers)


def fetch_payload(timeout: float = 30.0) -> tuple[dict[str, Any], list[str]]:
    """Fetch the simulator bootstrap JSON using one same-origin cookie session.

    ESO-Hub's Vue component performs a relative Axios GET from the simulator page.
    A direct urllib request can receive HTTP 401 because it does not first establish
    the same browser session/cookies. Warm the public simulator page, retain cookies,
    then make an XHR-shaped request to the initialize endpoint.
    """

    cookie_jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    with opener.open(_request(PAGE_URL), timeout=timeout) as response:
        response.read(1024)

    cookie_names = sorted({cookie.name for cookie in cookie_jar})

    request = _request(INITIALIZE_URL, referer=PAGE_URL, json_request=True)
    with opener.open(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="strict")

    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("ESO-Hub initialize endpoint returned a non-object payload")
    if not isinstance(payload.get("scripts"), list) or not isinstance(payload.get("skills"), list):
        raise ValueError("ESO-Hub initialize payload is missing scripts[] or skills[]")
    return payload, cookie_names


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch ESO-Hub's public Scribing Simulator initialize payload using a "
            "same-origin browser-like cookie session and save it as JSON."
        )
    )
    parser.add_argument(
        "--output",
        default="research/raw/esohub_scribing_initialize.json",
        help="Output JSON path (default: research/raw/esohub_scribing_initialize.json)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Network timeout in seconds")
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    try:
        payload, cookie_names = fetch_payload(args.timeout)
    except HTTPError as exc:
        print(f"ESO-Hub returned HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        if exc.code == 401:
            print(
                "The direct API requires more browser session state than urllib can establish. "
                "Open the initialize URL in your browser from the simulator page and save the JSON, "
                "then pass that file to import_scribing_simulator_initialize.py --source-json.",
                file=sys.stderr,
            )
        return 2
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        print(f"Could not fetch ESO-Hub Scribing data: {exc}", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("========================================")
    print(" ESO-HUB SCRIBING PAYLOAD FETCH")
    print("========================================")
    print(f"Simulator page: {PAGE_URL}")
    print(f"Initialize API: {INITIALIZE_URL}")
    print(f"Session cookies: {', '.join(cookie_names) if cookie_names else 'none observed'}")
    print(f"Scripts:         {len(payload.get('scripts') or []):,}")
    print(f"Skills:          {len(payload.get('skills') or []):,}")
    print(f"Saved:           {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
