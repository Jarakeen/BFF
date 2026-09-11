from __future__ import annotations

"""Aggregate ESO community news and discussion into one feed with a lightweight
trending signal.

Pulls two kinds of evidence:

- ESO-Hub's news RSS (patch summaries, popular-sets roundups, site features) as the
  reverse-chronological "Latest" backbone. Confirmed feed:
  https://eso-hub.com/en/news/feed.rss
- Reddit r/elderscrollsonline's public JSON listings as the "Trending" signal, since
  it carries real community engagement (score, comment count) that an RSS feed does
  not expose. No login or API key required for these read-only endpoints.

Both calls are plain unauthenticated GETs. This module does no caching of its own --
callers (the Qt page) decide when to refetch.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
import html
import re

import requests

_ESO_HUB_RSS_URL = "https://eso-hub.com/en/news/feed.rss"
_REDDIT_HOT_URL = "https://www.reddit.com/r/elderscrollsonline/hot.json?limit=25"
_REDDIT_NEW_URL = "https://www.reddit.com/r/elderscrollsonline/new.json?limit=25"

# Reddit's API rejects the default python-requests User-Agent with a 429/403. A
# descriptive, app-specific one is required, not just polite.
_USER_AGENT = "BFF-FoundryDock/1.0 (ESO build-optimization app; community news reader)"
_REQUEST_TIMEOUT = 10


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
    """Raised when a feed source could not be reached or parsed at all."""


class CommunityFeedService:
    """Fetches and merges ESO community news + trending discussion."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", _USER_AGENT)

    def fetch_latest(self) -> list[FeedItem]:
        """Reverse-chronological feed: ESO-Hub news + Reddit's newest posts, merged."""
        items: list[FeedItem] = []
        errors: list[str] = []

        try:
            items.extend(self._fetch_eso_hub_rss())
        except Exception as exc:  # network/parsing errors from either source shouldn't sink the other
            errors.append(f"ESO-Hub News: {exc}")

        try:
            items.extend(self._fetch_reddit(_REDDIT_NEW_URL))
        except Exception as exc:
            errors.append(f"Reddit r/elderscrollsonline: {exc}")

        if not items and errors:
            raise CommunityFeedError("; ".join(errors))

        items.sort(
            key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return items

    def fetch_trending(self) -> list[FeedItem]:
        """Reddit's own 'hot' ranking -- a mix of score and recent activity."""
        items = self._fetch_reddit(_REDDIT_HOT_URL)
        items.sort(
            key=lambda item: (item.score or 0) + (item.comment_count or 0) * 2,
            reverse=True,
        )
        return items

    # -- ESO-Hub RSS --------------------------------------------------

    def _fetch_eso_hub_rss(self) -> list[FeedItem]:
        response = self.session.get(_ESO_HUB_RSS_URL, timeout=_REQUEST_TIMEOUT)
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
                    source="ESO-Hub News",
                    published_at=published_at,
                    summary=description,
                )
            )
        return items

    # -- Reddit ------------------------------------------------------

    def _fetch_reddit(self, url: str) -> list[FeedItem]:
        response = self.session.get(url, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
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
