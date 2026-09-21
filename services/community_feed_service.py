from __future__ import annotations

"""Aggregate ESO community news and discussion into one feed with a lightweight
trending signal.

Sources, and why each one is here:

- Official ESO News (elderscrollsonline.com/en-us/rss/news) -- ZOS's own news feed.
  Covers Crown Store showcases, event announcements, and -- usefully -- PTS/Update
  preview posts ("Test ESO's Upcoming Adventures with Update 51 on the PTS") that
  double as early notice of big upcoming changes.
- ESO-Hub News (eso-hub.com/en/news/feed.rss) -- community-run news/build site,
  covers patch summaries and set-popularity roundups the official feed doesn't.
- Massively Overpowered, ESO tag (massivelyop.com) -- independent MMO games
  journalism that actually covers ESO regularly. Stands in for "gaming press"
  coverage generally (IGN's ESO coverage is too sparse to have its own reliable
  feed -- see note below).
- Reddit r/elderscrollsonline -- "hot" for Trending (genuine community engagement:
  score + comment count), "new" to round out Latest.

What's deliberately NOT here, and why:

- IGN: no current, reliable, machine-readable feed exists for ESO specifically
  (their old regional XML feeds are dead). Massively OP's coverage substitutes.
- GameMaps.com: it's a custom-maps/mods hosting site, not a news source -- its ESO
  section has no content posted.
- X/Twitter: reading tweets requires a paid API since 2023; there's no free,
  reliable way to pull ZOS's posts. The official news feed's PTS/preview posts
  cover most of the same "upcoming changes" ground instead.
- The official forums (forums.elderscrollsonline.com), including the Patch Notes
  category: that host's robots.txt disallows automated access, so this service
  doesn't fetch it even though the pages themselves are public.

All calls are plain unauthenticated GETs -- no API keys required. This module
does no caching of its own; callers (the Qt page) decide when to refetch.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
import html
import re
import time

import requests

_ESO_HUB_RSS_URL = "https://eso-hub.com/en/news/feed.rss"
_OFFICIAL_NEWS_RSS_URL = "https://www.elderscrollsonline.com/en-us/rss/news"
_MASSIVELYOP_RSS_URL = "https://massivelyop.com/tag/the-elder-scrolls-online/feed/"
_REDDIT_HOT_URLS = [
    "https://www.reddit.com/r/elderscrollsonline/hot.json?limit=25",
    "https://old.reddit.com/r/elderscrollsonline/hot.json?limit=25",
]
_REDDIT_NEW_URLS = [
    "https://www.reddit.com/r/elderscrollsonline/new.json?limit=25",
    "https://old.reddit.com/r/elderscrollsonline/new.json?limit=25",
]

# Reddit rejects the default python-requests User-Agent outright (429/403), and is
# also just generally more bot-wary than the RSS sources -- hence the two-URL
# fallback list above (www -> old.reddit.com) and the retry in _fetch_reddit.
_USER_AGENT = "BFF-FoundryDock/1.0 (ESO build-optimization app; community news reader)"
_REQUEST_TIMEOUT = 10
_MAX_AGE = timedelta(days=60)  # "nothing more than 2 months old"


@dataclass(frozen=True, slots=True)
class FeedItem:
    """One news article or discussion post, normalized across sources."""

    title: str
    url: str
    source: str
    published_at: datetime | None
    summary: str = ""
    score: int | None = None  # Reddit upvotes; None for RSS items.
    comment_count: int | None = None  # Reddit comments; None for RSS items.

    @property
    def search_text(self) -> str:
        return f"{self.title}\n{self.summary}\n{self.source}".casefold()


class CommunityFeedError(RuntimeError):
    """Raised when every source for a tab failed -- not when some did."""


class CommunityFeedService:
    """Fetches and merges ESO community news + trending discussion."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", _USER_AGENT)
        self.session.headers.setdefault(
            "Accept", "application/rss+xml, application/xml, application/json;q=0.9, */*;q=0.8"
        )

    def fetch_official(self) -> list[FeedItem]:
        """Just the official elderscrollsonline.com news feed, newest first."""
        items = self._fetch_rss(_OFFICIAL_NEWS_RSS_URL, "Official ESO News")
        return _sorted_recent(items)

    def fetch_latest(self) -> list[FeedItem]:
        """Reverse-chronological feed merging every source except Reddit's 'hot'."""
        items: list[FeedItem] = []
        errors: list[str] = []

        for url, source in (
            (_OFFICIAL_NEWS_RSS_URL, "Official ESO News"),
            (_ESO_HUB_RSS_URL, "ESO-Hub News"),
            (_MASSIVELYOP_RSS_URL, "Massively OP"),
        ):
            try:
                items.extend(self._fetch_rss(url, source))
            except Exception as exc:
                errors.append(f"{source}: {exc}")

        try:
            items.extend(self._fetch_reddit(_REDDIT_NEW_URLS))
        except Exception as exc:
            errors.append(f"Reddit r/elderscrollsonline: {exc}")

        if not items and errors:
            raise CommunityFeedError("; ".join(errors))

        return _sorted_recent(items)

    def fetch_trending(self) -> list[FeedItem]:
        """Reddit's own 'hot' ranking -- a mix of score and recent activity."""
        items = _filter_recent(self._fetch_reddit(_REDDIT_HOT_URLS))
        items.sort(
            key=lambda item: (item.score or 0) + (item.comment_count or 0) * 2,
            reverse=True,
        )
        return items

    # -- RSS (ESO-Hub / Official / Massively OP all use this) --------

    def _fetch_rss(self, url: str, source: str) -> list[FeedItem]:
        response = self.session.get(url, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)

        items: list[FeedItem] = []
        for node in root.findall("./channel/item"):
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            if not title or not link:
                continue
            description = _strip_html(node.findtext("description") or "")
            published_at = _parse_rfc822(node.findtext("pubDate"))
            items.append(
                FeedItem(
                    title=title,
                    url=link,
                    source=source,
                    published_at=published_at,
                    summary=description,
                )
            )
        return items

    # -- Reddit ------------------------------------------------------

    def _fetch_reddit(self, urls: list[str]) -> list[FeedItem]:
        """Try each mirror (www -> old.reddit.com). When Reddit rate-limits it
        often answers with an HTML interstitial rather than a 429 -- status 200,
        body isn't JSON -- so a bad response.json() call is retried once after a
        short pause before moving on to the next mirror, instead of surfacing a
        raw "Expecting value" parse error."""
        last_error: Exception | None = None
        for url in urls:
            for attempt in range(2):
                try:
                    response = self.session.get(url, timeout=_REQUEST_TIMEOUT)
                    response.raise_for_status()
                    try:
                        payload = response.json()
                    except ValueError:
                        raise CommunityFeedError(
                            "Reddit returned a non-JSON response (likely a rate limit) "
                            "instead of the post listing"
                        ) from None
                    return self._parse_reddit(payload)
                except Exception as exc:
                    last_error = exc
                    if attempt == 0:
                        time.sleep(1.5)  # brief backoff before retrying this same mirror once
        assert last_error is not None
        raise last_error

    @staticmethod
    def _parse_reddit(payload: dict) -> list[FeedItem]:
        children = ((payload.get("data") or {}).get("children")) or []
        items: list[FeedItem] = []
        for child in children:
            row = child.get("data") or {}
            if row.get("stickied"):
                continue
            title = str(row.get("title") or "").strip()
            permalink = row.get("permalink")
            if not title or not permalink:
                continue
            created = row.get("created_utc")
            published_at = (
                datetime.fromtimestamp(float(created), tz=timezone.utc)
                if created is not None
                else None
            )
            items.append(
                FeedItem(
                    title=title,
                    url=f"https://www.reddit.com{permalink}",
                    source="r/elderscrollsonline",
                    published_at=published_at,
                    summary=str(row.get("link_flair_text") or ""),
                    score=_safe_int(row.get("score")),
                    comment_count=_safe_int(row.get("num_comments")),
                )
            )
        return items


def _filter_recent(items: list[FeedItem]) -> list[FeedItem]:
    cutoff = datetime.now(timezone.utc) - _MAX_AGE
    # Items with no known date are kept -- excluding them would silently drop
    # otherwise-good results just because a source didn't supply a timestamp.
    return [item for item in items if item.published_at is None or item.published_at >= cutoff]


def _sorted_recent(items: list[FeedItem]) -> list[FeedItem]:
    items = _filter_recent(items)
    items.sort(
        key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_rfc822(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


__all__ = ["CommunityFeedService", "CommunityFeedError", "FeedItem"]
