from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import re
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
USER_AGENT = "BlackFeatherFoundry-CollectibleIconCollector/1.0"

COLLECT_ID_PATTERNS = (
    re.compile(r"\bcollectid\s*=\s*[\"']?(\d+)", re.IGNORECASE),
    re.compile(r"[?&]collectid=(\d+)", re.IGNORECASE),
    re.compile(r"[\"']collectible(?:_id|Id)[\"']\s*:\s*[\"']?(\d+)", re.IGNORECASE),
)
IMG_SRC_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class CollectibleRef:
    id: int
    name: str
    icon: str


@dataclass(frozen=True)
class Candidate:
    collectible_id: int
    url: str
    source_html: str
    score: int


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return value[:80] or "collectible"


def _normalize_name(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+-\s+UESP.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^Online:\s*", "", value, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _normalize_url(raw: str) -> str:
    value = html.unescape(raw.strip())
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("/"):
        return urllib.parse.urljoin("https://en.uesp.net/", value)
    return value


def _looks_like_image(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.casefold()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS) or "/thumb/" in path


def _image_urls(text: str) -> list[str]:
    urls: list[str] = []
    for raw in IMG_SRC_RE.findall(text):
        url = _normalize_url(raw)
        if _looks_like_image(url):
            urls.append(url)
    return urls


def _load_collectibles(db_path: Path) -> dict[int, CollectibleRef]:
    if not db_path.exists():
        raise FileNotFoundError(f"Collectibles database not found: {db_path}")

    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT id, name, COALESCE(icon, '') FROM collectible ORDER BY id"
        ).fetchall()
    return {
        int(row[0]): CollectibleRef(int(row[0]), str(row[1] or ""), str(row[2] or ""))
        for row in rows
    }


def _score_url(url: str, collectible: CollectibleRef) -> int:
    lower = urllib.parse.unquote(url).casefold()
    score = 0

    if "images.uesp.net" in lower:
        score += 8
    if "collect" in lower:
        score += 8
    if "on-icon" in lower:
        score += 3
    if "/thumb/" not in lower:
        score += 2

    icon_stem = Path(collectible.icon.replace("\\", "/")).stem.casefold()
    if icon_stem and icon_stem in lower:
        score += 20

    tokens = [token for token in re.findall(r"[a-z0-9]+", collectible.name.casefold()) if len(token) >= 4]
    score += min(8, sum(1 for token in tokens if token in lower))

    if "activeframe" in lower or "frame" in lower:
        score -= 25
    if "achievement" in lower:
        score -= 18
    if "logo" in lower or "favicon" in lower:
        score -= 25

    return score


def _candidates_for_file(path: Path, collectibles: dict[int, CollectibleRef]) -> list[Candidate]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    candidates: dict[tuple[int, str], Candidate] = {}
    source_html = str(path.resolve())

    for pattern in COLLECT_ID_PATTERNS:
        for match in pattern.finditer(text):
            collectible_id = int(match.group(1))
            collectible = collectibles.get(collectible_id)
            if collectible is None:
                continue
            start = max(0, match.start() - 4000)
            end = min(len(text), match.end() + 4000)
            for url in _image_urls(text[start:end]):
                score = 30 + _score_url(url, collectible)
                key = (collectible_id, url)
                previous = candidates.get(key)
                if previous is None or score > previous.score:
                    candidates[key] = Candidate(collectible_id, url, source_html, score)

    title_match = TITLE_RE.search(text)
    if title_match:
        title_key = _normalize_name(title_match.group(1))
        if title_key:
            matching = [c for c in collectibles.values() if _normalize_name(c.name) == title_key]
            if len(matching) == 1:
                collectible = matching[0]
                for url in _image_urls(text):
                    score = 10 + _score_url(url, collectible)
                    key = (collectible.id, url)
                    previous = candidates.get(key)
                    if previous is None or score > previous.score:
                        candidates[key] = Candidate(collectible.id, url, source_html, score)

    return list(candidates.values())


def discover(html_dir: Path, collectibles: dict[int, CollectibleRef]) -> dict[int, Candidate]:
    best: dict[int, Candidate] = {}
    html_files = sorted({*html_dir.rglob("*.html"), *html_dir.rglob("*.htm")})

    print(f"HTML files:          {len(html_files):,}")
    for index, path in enumerate(html_files, 1):
        for candidate in _candidates_for_file(path, collectibles):
            previous = best.get(candidate.collectible_id)
            if previous is None or candidate.score > previous.score:
                best[candidate.collectible_id] = candidate
        if index % 100 == 0:
            print(f"  scanned {index:,}/{len(html_files):,} pages; matched {len(best):,} collectibles")

    return best


def _extension(url: str, content_type: str = "") -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.casefold()
    if suffix in IMAGE_EXTENSIONS:
        return ".jpg" if suffix == ".jpeg" else suffix
    content_type = content_type.casefold()
    if "png" in content_type:
        return ".png"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    return ".png"


def _read_candidate_bytes(candidate: Candidate) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(candidate.url)
    if parsed.scheme in {"http", "https"}:
        request = urllib.request.Request(candidate.url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read(), response.headers.get("Content-Type", "")

    source_page = Path(candidate.source_html)
    local_ref = urllib.parse.unquote(parsed.path or candidate.url)
    local_path = (source_page.parent / local_ref).resolve()
    if not local_path.is_file():
        raise FileNotFoundError(f"saved page image not found: {local_path}")
    content_type = mimetypes.guess_type(local_path.name)[0] or ""
    return local_path.read_bytes(), content_type


def _download(candidate: Candidate, collectible: CollectibleRef, output_dir: Path, force: bool) -> tuple[str, str]:
    body, content_type = _read_candidate_bytes(candidate)

    if not body:
        raise RuntimeError("empty response")
    if content_type and not content_type.casefold().startswith("image/"):
        raise RuntimeError(f"unexpected content type {content_type!r}")

    ext = _extension(candidate.url, content_type)
    digest = hashlib.sha256(body).hexdigest()
    filename = f"{collectible.id}_{_slug(collectible.name)}{ext}"
    target = output_dir / filename

    if force or not target.exists() or target.stat().st_size == 0:
        target.write_bytes(body)
    return filename, digest


def collect(
    *,
    data_dir: Path,
    html_dir: Path,
    output_dir: Path,
    force: bool = False,
    no_download: bool = False,
) -> dict:
    db_path = data_dir / "eso.db"
    collectibles = _load_collectibles(db_path)
    print(f"Collectibles in DB:  {len(collectibles):,}")

    best = discover(html_dir, collectibles)
    print(f"Matched IDs:         {len(best):,}")

    output_dir.mkdir(parents=True, exist_ok=True)
    entries: dict[str, dict] = {}
    failures: list[dict] = []

    for number, collectible_id in enumerate(sorted(best), 1):
        candidate = best[collectible_id]
        collectible = collectibles[collectible_id]
        entry = {
            "id": collectible.id,
            "name": collectible.name,
            "source_url": candidate.url,
            "source_html": candidate.source_html,
            "score": candidate.score,
            "original_icon": collectible.icon,
        }
        try:
            if no_download:
                entry["file"] = ""
                entry["sha256"] = ""
            else:
                filename, digest = _download(candidate, collectible, output_dir, force)
                entry["file"] = filename
                entry["sha256"] = digest
            entries[str(collectible_id)] = entry
        except Exception as exc:
            failures.append({"id": collectible_id, "name": collectible.name, "url": candidate.url, "error": str(exc)})

        if number % 100 == 0:
            print(f"  processed {number:,}/{len(best):,} matched icons")

    manifest = {
        "version": 1,
        "database": str(db_path.name),
        "html_root": str(html_dir),
        "icon_root": str(output_dir.name),
        "collectible_count": len(collectibles),
        "matched_count": len(best),
        "downloaded_count": sum(1 for entry in entries.values() if entry.get("file")),
        "failure_count": len(failures),
        "entries": entries,
        "failures": failures,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest:            {manifest_path}")
    print(f"Icons ready:         {manifest['downloaded_count']:,}")
    print(f"Failures:            {len(failures):,}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest UESP collectible icons from saved HTML pages.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--html-dir", type=Path, default=None, help="Root containing saved .html/.htm pages. Defaults to data-dir.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Icon cache directory. Defaults to data-dir/collectible_icons.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing cached image files.")
    parser.add_argument("--no-download", action="store_true", help="Discover mappings and write manifest without downloading images.")
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    html_dir = (args.html_dir or data_dir).resolve()
    output_dir = (args.output_dir or (data_dir / "collectible_icons")).resolve()

    print("=" * 64)
    print(" Black Feather Foundry - Collectible Icon Collector")
    print("=" * 64)
    print(f"Data:                {data_dir}")
    print(f"Saved HTML:          {html_dir}")
    print(f"Output:              {output_dir}")
    print()

    collect(data_dir=data_dir, html_dir=html_dir, output_dir=output_dir, force=args.force, no_download=args.no_download)


if __name__ == "__main__":
    main()
