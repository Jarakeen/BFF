
- **Raid Review journal** — Live Raid notes are stored per Raid Plan attempt and indexed by date → trial on a dedicated Review page, with the full saved note shown in a large reading pane plus attempt number, pull start/end time, and duration.
- **Top Gear naming** — the former Capabilities surface is presented as Top Gear; Raid Plan Review now opens the run-note journal instead of Top Gear.
# BFF / FoundryDock Feature Index

This file is a working index of features, tools, workflows, and notable user-facing capabilities that exist in BFF / FoundryDock.

Its purpose is simple: **do not forget the useful, strange, ambitious, or unexpectedly nice things we build.**

This is **not** the development roadmap and should not be used as the authority for phase completion. See `MASTER_ROADMAP.md` for implementation status, validation requirements, and planned work.

When a new feature becomes usable or a meaningful capability is added to an existing feature, add a short entry here.

---

## App / General

- Desktop application
- Executable packaging for local distribution
- Friend/shareable executable builds
- Optional executable builds that exclude the Broadcast module
- Application update support
- Release-gated executable packaging with a positive asset allowlist instead of bundling the entire repository asset tree
- `RELEASE_STATUS.md` tracks working, in-progress, disabled, legacy/deprecated, and runtime-required release boundaries separately from the broader feature index
- `packaging/release_manifest.py` is the machine-readable release payload contract for approved assets, database seed data, clean first-install state, user-owned state, and forbidden legacy asset trees
- `tools/audit_release_candidate.py` validates the packaging boundary and can block final builds while runtime data files remain unclassified
- `packaging/build_release.ps1` builds versioned first-install packages and updater payloads only after the strict release audit and test gate pass
- Release updates preserve the live `eso.db`, settings, builds, roster/progress/session state, and other user-owned data rather than replacing them with developer copies
- Clean first-install releases create an empty canonical characters catalog so developer/test player identities are never shipped in a fresh package
- `app_version.py` remains the single source of truth for the application release version
- Multiple visual themes
- Theme-aware UI components
- Rylo theme and Rylo-specific visual assets
- Theme-aware cards, controls, tables, and result surfaces
- FoundryCard headings resolve semantic heading icons from the canonical `assets/icons` library before compatibility icon locations
- Semantic icon lookup accepts space, hyphen, underscore, singular/plural, and reviewed alias variants so theme-aware UI surfaces can use one meaning-oriented icon vocabulary without leaking missing filename text into card headings
- BFF sidebar branding uses the compact **BFF / RAID OPERATIONS** lockup and compass mark
- Urban Wilderness uses a single low-stimulation, red/green-independent raid-lead workflow with static artwork, no flashing UI effects, Roster as the landing surface, and Community News hidden while disabled
- Raid Engine overview accents and New Build entry adapt to Foundry teal/amber or Rylo's squared steel palette, with text and numeric progress cues alongside color
- Main overview keeps four cards in each dashboard row at desktop widths; compact labeled attribute meters use red Health, green Stamina, and blue Magicka in both visual themes
- Current Gear also lists the active profile's bookmarked sets, keeping the main dashboard's detail and goal rows at four cards each
- Main and Coverage share canonical saved-build effect evidence: available static sources, conditional sources, effects not identified, and unmapped or unaudited effects remain distinct; Coverage filters work without inferring assignments or uptime
- Coverage can load any saved Roster team directly and audit its assigned **base builds** for static buff/debuff coverage without requiring a Boss, Assignments, Comp Maker, or Optimization; contextual Team/Boss variants are only applied when a contextual workflow explicitly requests them
- Raid Engine dashboard sends explicit Team Optimization slot/build selections into a labeled Coverage scope; Coverage can switch between that team snapshot and all saved builds without inferring provider assignments
- Raid Engine dashboard summarizes static coverage evidence with distinct available, conditional, not-identified, and unverified labels rather than treating an unknown effect as missing
- Raid Plans provides a visible 12-chair trial-planning workspace where gamertag can be known before character, role, class, or build, and saved builds can be assigned without mutating existing Roster persistence
- Raid Plans now keeps the non-editable center note as a static quote panel, removes the redundant top Roles/Spots field-note card, and routes detailed assignment work to the dedicated Assignments surface
- Raid Plans can show trial-specific wide hero artwork for Cloudrest, Sunspire, and Dreadsail Reef; banners resolve from the selected plan identity, crop without distortion, fail closed for unmapped trials, and are bundled as compressed WebP release assets
- Readiness parchment notes use fixed-height field-journal pencil/sketch artwork; full-color city art is reserved for dark surfaces and decorative art cannot change page/card geometry
- Empty boss, mechanic, positioning, and Raid Map panels use distinct compact field-art placeholders for Foundry and Rylo, with visible labels that distinguish decorative art from reviewed encounter evidence
- Main character overview dashboard
- Role-aware application surfaces
- Archive page / archived data access
- Startup defers heavy independent pages including Achievements and the Collectibles category browser until first use; the visual Collectibles dashboard and Rotation Builder remain eager, and the lazy Collectibles browser reuses the dashboard's shared profile-aware service

---

## Character & Build Management

- Character records
- Multiple saved builds per character
- Separate Character and Build entities
- Saved build loading and editing
- Canonical build representation
- Character-owned progression separate from individual builds
- Build identity persistence
- Race selection
- Class selection
- Attribute configuration
- Gear configuration
- Armor traits
- Armor enchantments
- Jewelry traits
- Jewelry enchantments
- Front-bar and back-bar weapon configuration
- Skill selection
- Morph selection
- Ultimate selection
- Passive skill ranks
- Owned skill-line tracking
- Champion Point configuration
- Mundus selection
- Food selection
- Potion selection
- Scribed Skill support
- Build readiness / progression checks
- Character Progression interface
- Skill-passive purchasing controls
- Bulk **Buy All** controls for progression sections
- Saved-build comparison is available in Rotation Builder's generated **Compare** workflow; full encounter-aware build comparison remains future optimization work
- Build-linked performance evidence is surfaced through the Performance Dashboard rather than a separate Builds performance panel
- Save generated or modified builds for later reuse
- **Copy Build To...** creates an independent same-class build for another canonical character without copying player identity, character progression, team assignments, or Ready state
- **Save as Template** stores reusable role-level build setup with explicit class overlays; Templates are browsable from the Builds view and can be applied to another character
- Cross-class template application keeps shared role setup but fails closed on class/skill state when no matching class overlay exists, leaving those slots for review instead of guessing

---

## Build Import

- Screenshot/OCR-assisted build and character intake implementation is retained, but its user-facing control is temporarily disabled while raid-planning intake ownership is being stabilized
- Raid roster import from Excel workbooks, CSV, and JSON with a review preview before persistence
- Raid workbook detection supports player-specific multi-loadout sheets and sectioned team sheets with shared role/build templates
- Imported builds are matched to gamertags and saved through the canonical Player -> Character -> Build catalog only after character identity is resolved or confirmed
- Achievement progress import

---

## Exports & Sharing

- Neutral CSV exports for spreadsheet / structured-data interchange
- Theme-aware human-facing PDF exports for Builds and Roster
- Build / roster export workflows
- Discord-formatted roster sharing
- Shareable local app builds

---

## Character Overview Dashboard

- Character summary / overview
- Build summary information
- Achievement progress overview
- Completed-achievement counts and category progress for the selected profile
- Sticker Book and Mount ownership totals from saved profiles
- Raid schedule panel
- Pinned Performance Focus goals
- Saved Gear Lookup bookmarks by profile
- Ready checkbox on each saved build in the Phase 14 Builds inspector; the saved readiness state is also reflected on the Raid Engine Overview
- Saved-build static capability evidence with unverified and conditional states
- Active expedition and encounter labels refresh with the overview
- Compact visual progress indicators

---

## Builds Editor

- Edit canonical saved builds
- Character progression management
- Skill and passive ownership controls
- Champion Point configuration
- Gear and set editing
- Weapon-bar configuration
- Skill-bar configuration
- All Build Editor dropdowns use searchable autocomplete combo boxes with case-insensitive contains matching and clear controls
- Mundus / food / potion configuration
- Scribed Skills interface
- Build-linked performance context is available through the Performance Dashboard; the Builds inspector itself remains build/configuration focused
- Role-aware build information
- Context Variants provide sparse **Team**, **Boss**, and **Team + Boss** gear, weapon, Mundus, Champion Point, skill-bar, food, potion, and note overrides while unchanged fields inherit automatically
- Matching build variants resolve field-by-field as **Team + Boss -> Team -> Boss -> base build**, so a boss-specific tweak does not require cloning an entire build
- Conditional **Rotation** tab appears only when the selected build owns a saved completed rotation
- Phase 14 Builds command center provides first-class All, Mine, Team, Templates, Favorites, and Archive library views with compact search/class/role/content filtering and a persistent inspector area
- Build Favorites and Archive state are persisted as additive profile metadata keyed by canonical build id, so starring or archiving never duplicates or deletes the underlying saved build
- Build-level inherited gear baseline defaults to **Gold · CP160 · Truly Superb**; blank item values inherit the baseline while existing explicit values are preserved and differing values are counted as visible exceptions
- The Phase 14 inspector uses Overview, Gear, Skills, CP, Progression, Consumables, Scribing, and Notes tabs, with Gear grouped into Armor, Jewelry, Front Bar, and Back Bar summaries instead of one giant spreadsheet
- The Phase 14 library reasserts the approved library-left / inspector-right split after legacy Builds decorators finish, restores the selected-build dossier when older wrappers detach it, and presents only one visible New Build entry while continuing to route through the canonical Easy Mode creator
- Phase 14 Build polish moves the single **Create New Build** action beside Help as a solid-gold primary control, adds class icons and colorblind-safe role icons, decorates equipment/food/potion rows with the canonical icon library, and restores canonical ESO ability artwork to the Skills inspector cards
- Heavy canonical editors remain lazy from the command-center view: the outer editor tabs are hidden while browsing and appear only when Edit, Character Progression, or Scribed Skills is explicitly opened
- Build Edit remains the canonical inline editor, but **Save** and **Cancel** return directly to the Phase 14 Builds library/inspector instead of leaving the user stranded on the legacy Edit workspace
- Focused Build editors open only the requested section (identity, Armor, Jewelry, Front Bar, Back Bar, Skills, Champion Points, Consumables, Notes, and existing Scribing access) from the right-side dossier; the monolithic legacy editor is retained only as a compatibility fallback
- The Phase 14 right-side dossier uses compact grouped Gear cards, slot/class/role/consumable icon vocabulary, collapsible per-slot detail, a compact baseline/exception strip, More Actions menu, and a single gold Save action
- Base skill bars and Base Champion Points are labeled explicitly in the Phase 14 dossier; Team/Boss context variants inherit those base values until a sparse override is recorded
- The Phase 14 Overview visibly summarizes saved **Context Variants** and provides direct access to the canonical Team / Boss / Team + Boss variant editor instead of hiding it behind the legacy-editor fallback
- Build Gear popups and dossier summaries use the reviewed ESO trait icon vocabulary for weapon, armor, and jewelry traits while retaining the trait text as the accessible source of meaning
- Phase 14 uses a user-extensible semantic icon resolver that tolerates spaces, hyphens, underscores, capitalization, and localized Windows filename display quirks, then reasserts Builds icons at the final visible-page boundary

---

## Rotation Builder

- **Owned Phase 14 runtime** — Rotation Builder is registered through a single page-owned UI boundary rather than the legacy patched dashboard; safe direct integrations include recovery Heavy Attack stabilization from reserve pressure, required-effect Heavy Attacks, duration-aware visual timeline/uptime lanes with ability icons, reviewed encounter-demand visibility, current-vs-saved comparison, build-owned rotation persistence, saved notes/context metadata, and PDF export.
- Phase 14 keeps Rotation Builder as its own workspace, separate from Builds, while accepting the selected saved build as input
- Pre-generation command center exposes **Safe Progression**, **Balanced**, and **Maximum Output** intent presets over the existing canonical rotation controls rather than inventing a second planner state
- Preset-selected execution/sustain values remain visible, editable, show a **Customized** state after manual changes, and can be reset to the active preset defaults
- Rotation context is summary-first: the collapsed bar emphasizes character/build/trial/boss/difficulty, while Team remains available under **Edit Context** for assignment-sensitive generation
- Phase 14 Rotation uses the canonical theme-aware `assets/icons` vocabulary across context chips, intent presets, generated settings, obligation rows, advanced controls, and result navigation; larger intent/settings/obligation/action surfaces fill the two-column workspace instead of leaving the command center top-heavy
- Phase 14 Rotation polish adds visible labels beneath the context values, enlarges the intent/setting/obligation surfaces, makes Generate Rotation the solid-gold dominant action, suppresses redundant legacy header actions during setup, and keeps icon-led result navigation below the command center
- Build skills, gear procs, team duties, pressure windows, and advanced rules are presented as compact obligation summaries; unsupported evidence remains explicitly unresolved instead of being fabricated
- Timeline, Uptime & Resources, Explanations, Compare, and Save & Export are exposed as an icon-led result navigation row beneath the setup cards and remain disabled until a generated plan exists; the canonical result tabs stay available after entering a result view
- The Phase 14 Rotation page now owns its visible widgets and signals directly; the legacy patched dashboard is not constructed, avoiding deleted-Qt-label and repeated-reparenting failure paths.
- Context-chip polish is idempotent across repeated page visits, so reopening Rotation Builder does not stack duplicate Character/Build/Trial/Boss/Difficulty captions
- The Rotation Builder front page is constrained to four primary setup surfaces before generation: compact Context, Rotation Intent, Inputs & Obligations, and the result-navigation panel; intent icons are displayed above their labels and generated-setting rows expose explicit edit pencils
- Rotation Intent, Inputs & Obligations, and Generated Settings use the large gold section hierarchy from the Phase 14 mockup, while result navigation and semantic SVG icons are reasserted at the final visible-page boundary
- Roster > Characters portrait circle is editable: bundled defaults are discovered from `assets/avatar`, custom portraits are copied to user-owned `data/avatar`, and the selected avatar is persisted on the canonical character record rather than in `eso.db`
- **Generate Rotation** remains the single dominant setup action; save/export controls stay in the generated-result workflow

---

## Performance Dashboard

- Player performance dashboard
- Role-aware performance layouts
- Healer performance view
- Damage Dealer performance view
- Tank performance view
- Performance data loading from saved player/build context
- Role-specific metric visibility
- Group support / buff analysis
- Role-aware Performance Focus recommendations and pin-able improvement goals; Raid Engine Overview also exposes its Skills to Work On summary
- Build-linked performance context and ESO Logs build evidence

---

## Combat Reference

- Searchable combat-reference workspace
- Source and entry-type filtering
- Player-facing common mechanic names / raid callouts are displayed and searchable without replacing canonical mechanic identity
- Short reviewed **How to Mitigate** guidance gives a large, scan-friendly survival instruction for supported mechanics
- Human-readable gameplay-practice entries sourced from the shared gameplay-policy registry
- Canonical encounter-mechanic entries sourced through the shared encounter repository / projection
- Canonical combat-effect entries sourced read-only from `combat_effect`, `combat_effect_trigger`, and `combat_effect_interaction`
- Canonical gear sets, active skills, passives, and Champion Points are exposed as searchable Reference Data entries
- Skill and passive entries include their skill line in the display identity so same-name abilities do not silently collide
- Related boss / encounter names include their parent dungeon or trial when known, including reviewed dungeon identities whose raw boss import is missing
- Reviewed gear / skill / passive / Champion Point version history can be shown as a **History / Legacy** flavor section with source provenance
- Reference history is presentation-only trivia and is never consumed by combat math, rotation, optimization, provider resolution, or canonical mechanics runtime
- Status effects expose duration, tick interval, stack limit, immunity duration, triggers, and effect interactions when present
- Reviewed research enrichment adds provenance-bearing values from official patch notes and corroborating sources without silently promoting them into combat-math authority
- Core U41+ status-effect entries now include useful delivery and secondary-effect details for Burning, Chilled, Concussion, Diseased, Hemorrhaging, Overcharged, Poisoned, and Sundered
- Off Balance exposes official player-source duration, reapplication lockout, and non-consumption behavior
- Dreadsail Reef Hindered, Rattled, and Devitalized entries expose reviewed encounter context and debuff behavior with explicit confidence/provenance
- Bare `Not modeled` values are replaced in the normal Reference loading path by specific evidence-state language describing exactly what remains unknown or unreviewed
- Related effects are derived from explicit effect-interaction rows rather than inferred from prose
- Canonical Major / Minor named-effect entries sourced from `minmax.named_combat_buffs`
- Named-effect entries expose U50 standing semantics and explicit U51 semantic differences without mutating the U50 default
- Component-owned effects such as Vulnerability, Protection, Berserk, Slayer, Vitality, and Defile remain labeled as component-layer semantics instead of receiving invented standing-stat values
- Named-effect stacking guidance follows the canonical rule that duplicate copies of the same named effect/objective do not stack while Major and Minor variants remain distinct
- Reviewed ability providers are sourced read-only from the `ability_combat_effect` relationship table and enrich matching effect entries with ability, relationship, weapon, condition, confidence, and provenance
- Ability-provider identity uses canonical lower-snake-case `index_name` values; duplicate numeric ESO ability aliases are collapsed and never promoted to semantic identity
- Reviewed gear-set providers are projected from `minmax.gear_set_known_effects` through canonical gear-set rows without parsing bonus-description prose
- Versioned potion-trait providers expose U50 / U51 Alchemy named-buff mappings from `minmax.alchemy_potion_buff_semantics`
- Named-effect entries explicitly mark passive-provider coverage unresolved until one shared reviewed passive-provider authority exists
- Provider relationships are shown only when explicit source-backed mappings exist; missing provider mappings remain absent rather than being inferred from tooltip prose
- Encounter entries expose only structured known fields such as mechanic type, damage type, target count, movement / positioning / cleanse requirements, hazard state, fatal-failure state, interruptibility, phases, and provenance
- Structured role, content, default-behavior, confidence, exception, and modeling-requirement details
- Related-concept links and cross-reference text
- Evidence / provenance display per reference entry
- Per-entry death-review guidance
- **Used By FoundryDock** display showing which systems consume or are affected by the referenced rule
- Mechanic / attack visual placeholder retained for future artwork, combat-log samples, and positioning diagrams

---

## Roster

- **Teams decorative art** — the Teams lower-left panel uses the Urban Wilderness full-color night rectangle in a fixed-height crop; artwork cannot expand or reshape the surrounding workspace/cards.

- **Player avatar picker** — clicking the Character detail portrait opens the bundled `assets/avatar` choices; the selected portrait is stored on the canonical Player and follows all of that player's characters/builds.

- Player roster
- Character roster records
- Role assignment
- Build assignment
- Multiple builds associated with roster characters
- Load roster players into team workflows
- Preserve roster identity separately from build identity
- Save generated team builds back to roster characters
- Roster summary cards for Players, Characters, Teams, Availability, Recruitment, and Archive open their detailed workspaces inline beneath the card bar instead of launching modal pop-ups
- Roster top cards use stable fixed geometry, semantic badge/icon treatment, and the existing Collectibles number-sheet contract without allowing artwork to resize the page
- The active Roster dashboard retires the old raven/street filler panels entirely; full-color art is not placed on parchment surfaces
- Players keeps a visible people table beside the editable Player Record instead of opening a form-only detail view
- Character detail uses a compact profile-style panel for player, class, race, role, teams, status, and saved-build count without showing Builds or Assignments tabs
- Assignment **Selected Spot** uses a structured profile card for player, character, role, primary/secondary duty, gear status, linked build, and notes with direct Build/Rotation/Edit Duties actions
- Import external raid rosters by merge rather than replacement, preserving unrelated players, teams, characters, and saved builds
- Imported build/team assignments are attached to the canonical gamertag/character/build identities when the import can resolve them uniquely
- Personnel keeps explicit **Known Aliases** for old gamertags, Discord names, and raid-sheet names; aliases are learned from manual entry, renames, or explicit merges rather than guessed from similarity
- **Merge Players…** consolidates two user-confirmed Personnel identities, preserves their teams and assignment state, moves canonical characters/builds under the kept player identity, creates backups, and remembers discarded names as future import aliases
- Future roster imports reuse exact learned aliases as player identity evidence, including all canonical characters already known for that player
- Assignments persist separately for each **roster member + team**, so one character can have different normal jobs on different teams
- **Comp Builder roster-first planning** keeps imported/selected groups at their real ESO size (4 or 12), shows Player from first paint with empty seats labeled `Recruit`, accepts **Load Team** directly on the page, treats Recruit as an open prescription slot that cannot borrow another player's saved build, scopes saved-build choices to the loaded player, and preserves known player/character identity when a build decision is still unresolved; the approved Phase 14 Work-chat shell is organized as **Raid Brief -> Recommended Team Plan + Why This Plan -> Team Health**, with Generate Team Plan as the dominant action and legacy matrix/evidence infrastructure kept behind the visible workflow; the Why This Plan recommendation and two alternative surfaces are selectable gear-choice cards that apply the chosen evidence-backed candidate to the highlighted chair, use only canonical five-piece set projections for those two-set packages, and expose confidence as a color-coded evidence state

## Phase 14 Builds progression ownership
- The Builds dossier now owns character progression access through a dedicated **Progression** tab.
- **Passive Skills** covers character-owned skill-line access and purchased passive ranks shared by every build for that character.
- **Passive Champion Points** covers non-slottable Champion stars shared by every build; slotted Champion Points remain build-specific on the normal CP tab.
- Character Progression provides global **Buy All Passive Skills** and **Buy All Passive CP** actions, while retaining per-skill-line and per-discipline controls for narrower edits.
- The old monolithic Build Editor, Character Progression workspace tab, and Scribed Skills workspace tab are hidden from the normal Phase 14 workflow and retained only as compatibility/fallback infrastructure.


## Rumors collection ledger
- Imported UESP Rumors stored in `collectible_rumor` / `collectible_rumor_hint` now populate the **Rumors** Collectibles page instead of showing an empty ledger.
- Rumor ownership is profile-aware through a separate additive `collectible_rumor_progress` table; the canonical collectible catalog is not rewritten or merged.
- Rumor detail shows the imported start hint plus ordered rumor-hint text, and Rumors progress is reflected on the Collectibles dashboard.


## Team Discord links
- Teams visibly expose an optional Discord invite/server/channel URL alongside raid schedule, time zone, and current focus on the current Phase 14 Teams editor.
- The Discord URL is persisted additively on the existing `team` record and reloads with the selected team.
\n\n## Raid Plan\n\n- Trial-specific artwork banners appear in Raid Plan Selected Plan and Live Raid Current Encounter hero surfaces.\n\n\n## UI\n\n- Shared app page headers use the Collectibles-style uppercase Montserrat treatment with muted-gold text and restrained letter spacing; page-specific subtitles and context controls remain unchanged.

- **Rotation command-center visual contract** — Rotation Context stays on one compact row, intent tiles use restrained blue/silver hover/selected treatment, and generated results use the five-button icon navigator with a locked pre-generation state instead of exposed raw Qt tabs.

- **Raid Plan note** — the parchment Plan Note on Raid Plan Overview is editable and persists with the exact `RaidPlan` snapshot; loading another plan restores that plan's own note.
\n- **Rotation Builder Phase 14 shell** — Rotations are restored through an owned command-center page that preserves the current presentation while calling the existing generation and sustain engines directly; the legacy patched dashboard is not constructed at startup.\n