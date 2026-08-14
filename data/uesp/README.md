# UESP Encounter Knowledge Base

A local, structured knowledge base of ESO trial/dungeon/arena
encounters, built from [UESP](https://en.uesp.net/) — The Unofficial
Elder Scrolls Pages.

## Source & license

- All data here is pulled through **UESP's official MediaWiki API**
  (`https://en.uesp.net/w/api.php`), the same interface UESP,
  Wikipedia, and every other MediaWiki site expose for programmatic
  access. Nothing here is scraped from rendered pages by a browser
  automation tool, and nothing bypasses `robots.txt` — `api.php`
  isn't a path `robots.txt` restricts; it's the documented API
  surface.
- UESP's content is licensed under **Creative Commons
  Attribution-ShareAlike 2.5** (CC BY-SA 2.5). That means reuse is
  permitted, provided the source is credited. Every record in this
  knowledge base carries a `source` block with the exact wiki page
  URL, page title, revision id, and retrieval date, for that reason —
  keep that block intact if you republish or redistribute this data.
- The importer never invents information. Fields it can't find on
  the source page are left empty or omitted, not guessed or filled
  in with plausible-sounding text.
- No raw HTML or wikitext is stored in this directory. The importer's
  network cache (`.cache/`) does hold raw API responses, but that's
  separate from the structured JSON below and exists purely so
  re-running the importer doesn't refetch unchanged pages.

## Layout

```
data/uesp/
    trials/<id>.json       # one file per trial
    dungeons/<id>.json     # one file per dungeon
    arenas/<id>.json       # one file per arena
    bosses/<id>.json       # one file per boss, linked to its parent content
    index.json             # lightweight lookup: id -> name, source URL, revision
    import_log.jsonl       # one line per import attempt (imported/skipped/error)
    .cache/                # raw API responses, keyed by request hash
```

Every `<id>` is a stable slug of the UESP page title (e.g.
`Online:Xalvakka` → `xalvakka`; `Online:Ash Titan (Rockgrove)` →
`ash_titan_rockgrove` — disambiguators are kept, not stripped, so two
same-named bosses from different content never collide).

### Boss record shape

```json
{
    "id": "xalvakka",
    "name": "Xalvakka",
    "content_id": "rockgrove",
    "content_name": "Rockgrove",
    "location": "Rockgrove, Tower of the Five Crimes",
    "species": "Harvester",
    "reaction": "Hostile",
    "health": { "normal": "...", "veteran": "...", "hardmode": "..." },
    "abilities": [ { "name": "...", "description": "..." } ],
    "phases": [ { "label": "Phase 2", "threshold": "70%", "description": "" } ],
    "dialogue": [ { "speaker": "...", "line": "...", "trigger": "At 70%:" } ],
    "difficulty_notes": {
        "normal_veteran_differences": ["..."],
        "hardmode_info": ["..."]
    },
    "strategy_notes": ["..."],
    "notes": ["..."],
    "related_npcs": ["..."],
    "related_quests": ["..."],
    "achievements": [ { "id": "...", "name": "..." } ],
    "summary": "...",
    "source": {
        "url": "https://en.uesp.net/wiki/Online:Xalvakka",
        "page_title": "Online:Xalvakka",
        "revision_id": 123456,
        "retrieved_at": "2026-08-08T22:00:00Z",
        "license": "CC BY-SA 2.5 (UESP)"
    }
}
```

Trial/dungeon/arena records follow the same idea at the content
level: `id`, `name`, `content_type`, `summary`, `location`,
`boss_ids` (linking to `bosses/`), `achievements`, `related_npcs`,
`notes`, and the same `source` block.

## CLI usage

```bash
python tools/import_uesp.py --content "Rockgrove"
python tools/import_uesp.py --boss "Bahsei"
python tools/import_uesp.py --all-trials
python tools/import_uesp.py --all-dungeons
python tools/import_uesp.py --all-arenas
python tools/import_uesp.py --all
```

`--content` fetches a trial/dungeon/arena overview page, follows any
boss links found in its "Bosses"/"Encounters" section, and imports
each of those too — so one `--content` call fills in a full content
record plus every boss under it. Content type (trial/dungeon/arena)
is detected automatically from the page's own wiki categories;
`--content-type` is only a fallback for the rare page where that
detection comes up empty.

Other flags:

- `--force` — re-import even if the stored revision id already
  matches what's on the wiki (normally skipped, see below).
- `--rate-limit SECONDS` — minimum delay between UESP API requests
  (default `2.0`).
- `--data-root PATH` — write somewhere other than `data/uesp/`.

Exit code is `1` if any item failed, `0` otherwise. A summary line
and any per-item errors print at the end of the run; every attempt
(imported, skipped, or errored) is also appended to
`import_log.jsonl`.

This only writes JSON under `data/uesp/`. To load that into
`data/eso.db`, run `tools/import_to_db.py` next — see Architecture
below.

## Rate limiting & caching

- Requests to UESP are **serial**, spaced at least `--rate-limit`
  seconds apart (default 1 request per 2 seconds) regardless of how
  fast the importer itself wants to fire them.
- Every raw API response is cached to `.cache/` by a hash of its
  request parameters. An unchanged request never touches the network
  twice — delete `.cache/` to force a full refetch, or use `--force`
  to re-parse and re-save records even when the cache already has
  the data.
- The client sends a descriptive `User-Agent` identifying this tool,
  per standard MediaWiki API etiquette.

## Change detection & de-duplication

Every record's `source.revision_id` is the UESP wiki revision it was
parsed from. Before re-parsing a page, the importer checks the
revision id already stored on disk against the one the API just
returned for that title; if they match, the page is skipped (logged
as `skipped_up_to_date`) and nothing is re-written. Records are
always looked up and overwritten by their stable `id`, so re-running
an import never creates a duplicate file — it either updates the
existing one (new revision) or leaves it untouched (same revision).

## Architecture

This is a two-stage pipeline, and the stages don't know about each
other beyond the JSON files on disk:

**Stage 1 - fetch & normalize (this directory's contents):**
- `services/uesp/uesp_client.py` — talks to `api.php` only. Rate
  limiting, caching, retries.
- `services/uesp/uesp_parser.py` — turns a fetched page's rendered
  HTML into the structured dataclasses below. Parses UESP's HTML
  output (not raw wikitext) because it's the stable structural
  contract every page shares — headings, tables, and definition
  lists render consistently even though template internals vary
  page to page.
- `services/uesp/uesp_store.py` — writes the JSON files in this
  directory, including `index.json` and revision-based change
  detection.
- `services/uesp/uesp_importer.py` — orchestrates the three pieces
  above and owns `import_log.jsonl`.
- `models/uesp_models.py` — the dataclasses themselves
  (`UespBoss`, `UespContent`, `UespAchievement`, etc.). Deliberately
  separate from `models/boss.py`, which describes the app's own
  archive-run format rather than UESP-sourced facts.
- `tools/import_uesp.py` — the CLI for this stage. Talks to the
  network; never touches a database.

**Stage 2 - load into eso.db (`services/eso_db/`):**
- `services/eso_db/schema.py` — the SQLite DDL: `content` and
  `bosses` tables plus child tables (`boss_abilities`,
  `boss_phases`, `boss_dialogue`, `content_achievements`, etc.) keyed
  by the parent's stable id.
- `services/eso_db/eso_db_importer.py` — reads the JSON produced by
  stage 1 and writes rows. This module has **no import dependency on
  `services/uesp/`** — it only knows the JSON shape documented above.
  Re-running it is idempotent: each parent record's child rows are
  deleted and re-inserted inside one transaction, so nothing
  duplicates.
- `tools/import_to_db.py` — the CLI for this stage. Never touches
  the network; only reads `data/uesp/*.json` and writes
  `data/eso.db`.

Run them as two separate steps:

```bash
python tools/import_uesp.py --all       # network -> data/uesp/*.json
python tools/import_to_db.py            # data/uesp/*.json -> data/eso.db
```

Nothing under `ui/` imports either stage.

## Known limitations

- Phase/mechanic structure is extracted heuristically from prose
  (e.g. "Phase 2 starts when health reaches 70%"). Pages that
  describe phases in unusual phrasing may end up with an empty
  `phases` list even though the strategy text (preserved in full
  under `strategy_notes`) describes them.
- Boss discovery from a content page's "Bosses" section is
  link-based; a content page without a clearly linked boss list will
  import with `boss_ids: []` — use `--boss` directly for those.
- The HTML section-skipping logic (used to ignore navboxes/table-of-
  contents blocks) is a simple matching-tag heuristic, not a full DOM
  parser. On pages with unusual nested markup this can occasionally
  leave a stray non-content line in a section; it will never
  fabricate content that isn't literally on the page.
