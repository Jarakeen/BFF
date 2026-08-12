# services/uesp/uesp_client.py
"""
Thin HTTP client for UESP's official MediaWiki API (api.php).

This is the only file in the importer allowed to open a network
connection. It never scrapes rendered wiki pages directly - every
request goes through api.php (action=parse / action=query), which is
UESP's documented, intended way to access content programmatically.
UESP is a standard MediaWiki install; api.php is the same interface
Wikipedia and every other MediaWiki site exposes for exactly this
kind of use.

Etiquette this client follows, per MediaWiki's own API:Etiquette
guidance and UESP's own upgrade log (which documents banning bots
that ignored robots.txt or hit the site at 500+ req/sec):
  - A descriptive User-Agent identifying this tool.
  - A minimum delay between requests (default 1s), enforced even if
    the caller fires requests back-to-back.
  - Every raw response is cached to disk, so re-running the importer
    for content that hasn't changed makes zero network requests.
  - Serial requests only - no concurrency, no request pooling.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_ENDPOINT = "https://en.uesp.net/w/api.php"

USER_AGENT = (
    "BlackFeatherFoundry-UespImporter/1.0 "
    "(local ESO encounter knowledge base; "
    "https://github.com/Jarakeen/BFF)"
)


class UespClientError(Exception):
    """Raised when the UESP API returns an error or an unusable response."""


@dataclass
class UespPage:
    """A single wiki page, as returned by action=parse."""

    title: str
    page_id: int
    revision_id: int
    wikitext: str
    html: str
    categories: list[str]


class UespClient:
    """
    Rate-limited, caching client for UESP's api.php.

    All requests are GET, serial, and spaced at least
    ``min_request_interval`` seconds apart. Every raw response is
    cached to ``cache_dir`` so identical requests never hit the
    network twice - this is separate from data/uesp's structured
    JSON output, which never contains raw HTML or wikitext.
    """

    def __init__(
        self,
        cache_dir: Path,
        min_request_interval: float = 2.0,
        user_agent: str = USER_AGENT,
        timeout: float = 15.0,
        max_retries: int = 3,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.min_request_interval = min_request_interval
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries

        self._last_request_time: float = 0.0

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_page(self, title: str, use_cache: bool = True) -> UespPage:
        """
        Fetch a page's wikitext, rendered HTML, revision id, and
        categories in a single API call (action=parse).
        """

        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext|text|revid|categories",
            "formatversion": "2",
            "format": "json",
        }

        data = self._request(params, use_cache=use_cache)

        if "error" in data:
            raise UespClientError(
                f"UESP API error for '{title}': "
                f"{data['error'].get('info', data['error'])}"
            )

        parse = data.get("parse")
        if not parse:
            raise UespClientError(
                f"UESP API returned no page data for '{title}'."
            )

        categories = [
            category.get("category", "")
            for category in parse.get("categories", [])
        ]

        return UespPage(
            title=parse.get("title", title),
            page_id=int(parse.get("pageid", 0)),
            revision_id=int(parse.get("revid", 0)),
            wikitext=parse.get("wikitext", ""),
            html=parse.get("text", ""),
            categories=categories,
        )

    def get_category_members(
        self,
        category: str,
        member_type: str = "page",
        use_cache: bool = True,
    ) -> list[str]:
        """
        Return the titles of all pages in a category, following
        continuation until exhausted. ``category`` should NOT
        include the "Category:" prefix.
        """

        titles: list[str] = []
        continue_token: dict[str, str] = {}

        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category}",
                "cmtype": member_type,
                "cmlimit": "500",
                "formatversion": "2",
                "format": "json",
                **continue_token,
            }

            data = self._request(params, use_cache=use_cache)

            if "error" in data:
                raise UespClientError(
                    f"UESP API error listing category '{category}': "
                    f"{data['error'].get('info', data['error'])}"
                )

            members = data.get("query", {}).get("categorymembers", [])
            titles.extend(member["title"] for member in members)

            if "continue" in data:
                continue_token = data["continue"]
            else:
                break

        return titles
    def get_categories(
        self,
        prefix: str = "",
        use_cache: bool = True,
    ) -> list[str]:
        """
        Return UESP category names, optionally filtered by prefix.

        Used for discovering the correct category structure before
        adding a new crawler/import path.
        """

        categories: list[str] = []
        continue_token: dict[str, str] = {}

        while True:
            params = {
                "action": "query",
                "list": "allcategories",
                "acprefix": prefix,
                "aclimit": "500",
                "formatversion": "2",
                "format": "json",
                **continue_token,
            }

            data = self._request(
                params,
                use_cache=use_cache,
            )

            if "error" in data:
                raise UespClientError(
                    "UESP API error listing categories: "
                    f"{data['error'].get('info', data['error'])}"
                )

            members = data.get(
                "query",
                {}
            ).get(
                "allcategories",
                []
            )

            categories.extend(
                item["category"]
                for item in members
            )

            if "continue" in data:
                continue_token = data["continue"]
            else:
                break

        return categories
    
    # --------------------------------------------------
    # Internals
    # --------------------------------------------------

    def _request(self, params: dict[str, str], use_cache: bool) -> dict[str, Any]:

        cache_key = self._cache_key(params)
        cache_path = self.cache_dir / f"{cache_key}.json"

        if use_cache and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        payload = self._fetch_with_retries(params)

        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return payload

    def _fetch_with_retries(self, params: dict[str, str]) -> dict[str, Any]:

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):

            self._respect_rate_limit()

            try:
                return self._fetch(params)

            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                backoff = self.min_request_interval * (2 ** (attempt - 1))
                time.sleep(backoff)

        raise UespClientError(
            f"Failed to reach UESP API after {self.max_retries} attempts: {last_error}"
        )

    def _fetch(self, params: dict[str, str]) -> dict[str, Any]:

        url = f"{API_ENDPOINT}?{urllib.parse.urlencode(params)}"

        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent},
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")

        return json.loads(body)

    def _respect_rate_limit(self) -> None:

        elapsed = time.monotonic() - self._last_request_time

        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        self._last_request_time = time.monotonic()

    @staticmethod
    def _cache_key(params: dict[str, str]) -> str:
        normalized = json.dumps(params, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
