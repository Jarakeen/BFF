
- **Raid Review journal** — Live Raid notes are stored per Raid Plan attempt and indexed by date → trial on a dedicated Review page, with the full saved note shown in a large reading pane plus attempt number, pull start/end time, and duration.
- **Top Gear naming** — the former Capabilities surface is presented as Top Gear; Raid Plan Review now opens the run-note journal instead of Top Gear.
# BFF / FoundryDock Feature Index

- **Phase 14 deterministic combat-simulation kernel** — consumes canonical `EffectiveBuildSnapshot` + Phase 13 `RotationPlan`, preserves exact action ordering and active-bar authority, fails closed on identity/bar violations, and emits explicit unresolved consequences until existing resource/healing/damage/proc engines are wired.
- **Phase 14 healer Magicka simulation bridge** — projects named healer skill costs and ordinary recovery through the existing Rotation/Phase 4 sustain authority, merges auditable resource transitions into the deterministic simulation stream, and keeps non-resource skill outcomes explicitly unresolved until their owning engines are connected.
- **Phase 14 healer output bridge** — reuses canonical healer component math to emit direct-heal simulation events and explicit periodic/delayed/channel healing seeds; exact periodic tick placement remains unresolved until reviewed runtime timing evidence is available.
- **Phase 14 reviewed healer periodic timing** — expands periodic-heal seeds into deterministic heal ticks only from canonical cadence/duration plus explicitly reviewed runtime timing/refresh evidence; supports reviewed fixture loading without promoting candidate evidence or guessing fixture paths.
- **Phase 14 reviewed healer skill effects** — projects reviewed bounded cast effects into deterministic apply/expire windows, reusing canonical skill-effect identity and runtime stacking; Combat Prayer Minor Resolve is the first control, while exact group recipients remain unresolved until target state is modeled.

- **Phase 12.5 canonical closeout audit** — a read-only real-data audit checks persisted Raid Plans against reusable saved Builds and Roster identities, preserving recruit/open chairs, stable player/character/build IDs, locked class/role/gear choices, assignment provenance, explicit unresolved state, temporary-only persistence round-trips, and Optimizer Adviser non-mutation.

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
- Sidebar top-level groups are ordered **Raid → Team → Build → Encounter → Review → Achievement → Collectibles → Tools → Settings** while preserving the existing child destinations within those groups; optional Broadcast tools stay inside Tools instead of creating another top-level section
- Urban Wilderness uses a single low-stimulation, red/green-independent raid-lead workflow with static artwork, no flashing UI effects, Roster as the landing surface, and Community News hidden while disabled
- **Live Raid field-console styling** — the existing Live Raid cards use the compact nocturnal dispatch treatment from the approved mockups: shallow warm-gold card borders, blue-black interiors, compact status tiles, flattened Raid Spots table, denser Callouts / Recent Events / Coverage surfaces, a shallow Next 60 Seconds panel, and parchment reserved for Quick Notes / Run Sheet. Styling never fabricates telemetry: roster count remains planned state, phase remains planned context, and observed state stays explicitly unavailable until a real runtime source exists.
- Raid Engine overview accents and New Build entry adapt to Foundry teal/amber or Rylo's squared steel palette, with text and numeric progress cues alongside color
- Main overview keeps four cards in each dashboard row at desktop widths; compact labeled attribute meters use red Health, green Stamina, and blue Magicka in both visual themes
- Current Gear also lists the active profile's bookmarked sets, keeping the main dashboard's detail and goal rows at four cards each
- Main and Coverage share canonical saved-build effect evidence: available static sources, conditional sources, effects not identified, and unmapped or unaudited effects remain distinct; Coverage filters work without inferring assignments or uptime
- Coverage is **saved-Raid-Plan scoped** in the Raid workflow: its visible selector lists only persisted trial-specific Raid Plans, including trial and difficulty context. Reusable Roster teams and library-wide saved-build audits remain lower-level/internal capabilities and are not presented as competing Coverage scopes. Raid Plan planned gear can contribute reviewed set-only Conditional coverage evidence without pretending a full Saved Build exists.
- Raid Engine navigation opens Coverage without injecting transient Team Optimization or Roster-team state; provider evaluation follows the selected persisted Raid Plan as the trial-specific source of truth.
- Raid Engine dashboard summarizes static coverage evidence with distinct available, conditional, not-identified, and unverified labels rather than treating an unknown effect as missing
- Raid Plans provides a visible 12-chair trial-planning workspace where gamertag can be known before character, role, class, or build, and saved builds can be assigned without mutating existing Roster persistence
- Raid Plans now keeps the non-editable center note as a static quote panel, removes the redundant top Roles/Spots field-note card, and routes detailed assignment work to the dedicated Assignments surface
- Raid Plan footer keeps only the blue primary Save action on the right; cross-page tools are reached through normal navigation instead of footer handoff buttons
- Assignments separates buff/debuff ownership from utility/mechanic jobs, combines primary/secondary support responsibilities into one visible column, moves notes into Selected Spot, and shows Plan Snapshot instead of a Mechanic Coverage link card. Each chair also has a small free-text **Source** annotation for planning shorthand such as `WW`, class skill, or proc set; it is display context only and never substitutes for the actual buff/debuff assignment.
- App navigation uses a shared unsaved-change contract: editable pages that report pending changes receive Save / Discard / Cancel before page navigation
- Raid Plans can show trial-specific wide hero artwork for Cloudrest, Sunspire, and Dreadsail Reef; banners resolve from the selected plan identity, crop without distortion, fail closed for unmapped trials, and are bundled as compressed WebP release assets
- Comp Builder now owns canonical `CompPlanState` **before or after Raid Plan creation**. Team/Roster/Assignments intake can create an unbound planning state directly; Save finalizes it into a new non-colliding Raid Plan and rebinds the same Comp session, while a Raid Plan-bound session updates that same plan. Supported Phase 14 save does not require generated-roster drafts, create Personnel, or overwrite reusable saved Builds/Roster membership.
- Phase 14 Comp Maker has route-independent canonical ownership: direct-open sessions, Roster/Assignments handoffs, and existing Raid Plan handoffs all operate on `CompPlanState`. Loaded Raid Plans finish hydration clean; unbound planning supports Save/Discard and **Send to Raid Plan** through the same canonical persistence path.
- Phase 14 Comp Maker selected-chair setup provides a searchable **full Gear Catalog** assignment control. Raid leads can add or remove planned sets directly from canonical Comp state; smart recommendations remain optional suggestions and no longer define which gear is accessible.
- Phase 14 Comp Maker memoizes canonical Team Health, selected-chair proposal analysis, and selected-chair candidate discovery by immutable planning inputs so ordinary UI repaint/selection signals do not repeat expensive whole-team evaluation.
- Phase 14 Comp Maker never performs a live ESO Logs network request during application startup or ordinary trial selection. Those paths refresh local roster/reference candidates and clear stale trial observations; current ranked-team evidence is fetched only through the explicit **Refresh Build Sources** action, so an unavailable or slow ESO Logs response cannot prevent the application window from opening.
- Phase 14 Comp Maker selected-chair planning exposes compact **Primary Coverage**, **Backup Coverage**, and free-text **Source** controls backed by canonical assignment state, so effects such as Crusher can be planned directly without a mechanic-specific widget. Existing `planned_skills` are visibly summarized in the Why panel with the full skill list on hover, even when no recommendation candidate exists.
- Phase 14 Comp Maker **Fill Empty Skills** can seed an empty chair skill plan from a saved build with known skills or a complete reference template. It never replaces existing `planned_skills`, respects the Skills lock, and keeps incomplete references plus observed ESO Logs abilities as suggestion/evidence only. Generic recommendation Apply continues to leave skills untouched.
- Phase 14 **Selected Chair Adviser** compares a candidate against canonical `CompPlanState` before applying it, showing planned coverage gained/lost, assignment-evidence improvements/regressions, reviewed source-evidence changes, duplicates added/removed, and independently preserved lock fields. The Apply action uses the same proposal service as Preview for Raid Plan-bound sessions.
- Phase 14 Comp Maker is **assignment-aware composition planning**: bulk Fill from Roster / Auto-Fill operates on canonical `CompPlanState` to fill unresolved chair/build decisions while preserving explicit/locked choices, consuming each real saved player at most once, preferring canonical player/character/build identity, and treating explicit Primary/Backup responsibilities from Assignments as hard provider requirements for that chair. Comp Maker chooses a compatible build/gear/skill package where evidence proves the assigned effect; it does not invent new responsibility ownership from generic missing Team Health rows. Team Health remains visible for missing/duplicate composition feedback, while Optimizer improves an already valid saved plan afterward.
- Phase 14 **Team Optimization Recommendation Workbench** opens one exact saved Raid Plan as a read-only 12-chair snapshot and ranks canonical plan blockers, missing providers, conditional execution, redundant providers, and Foundry evidence debt. Recommendations expose current/proposed review state, affected providers, tradeoffs, confidence, and honest coverage/build-resolution summaries; unsupported survival, sustain, uptime, and raid-DPS projections remain visibly unevaluated. Review selection never overwrites a Build or Raid Plan, and scenario saving stays disabled until a canonical reversible proposal model exists. Its scope banner distinguishes no handed-off plan from a loaded empty or partial team and explains that incomplete teams remain valid review input while open chairs are reported as blockers. Normal application startup now constructs only this lightweight Phase 14 workbench: the retired editable Optimization page, generated-roster draft bridge, legacy canonical-analysis presentation, and Optimization provider-workload widgets are not initialized at launch. Saved-build loading, capability resolution, and the reusable Raid Plan Adviser service are lazy-created only when `set_raid_plan_adviser_scope` receives an exact saved Raid Plan. `console:6` remains the route identity, and `tools/profile_team_optimization_startup.py` records constructor time separately from first plan-scope analysis without writing user data.
- **Coverage planning semantics:** Raid Plan Coverage answers whether the planned group has a source for each tracked buff/debuff. Planned gear, reviewed planned skills, reviewed class-passive sources with their planned trigger skill line, conditional/proc sources, and explicit provider assignments count as **Covered** for planning; self-only skill effects are excluded. Evidence labels separately describe Supported, Conditional, Planned/runtime-unproven, duplicate ownership, or Missing. Rotation and Raid Review remain responsible for execution and observed uptime.
- Phase 14 Comp Maker Team Health **Covered** tile exposes its current default-required buff/debuff checklist on hover, sourced from the same canonical Team Health requirement list rather than duplicated UI text.
- Phase 14 Comp Maker Team Health now reads the canonical `CompPlanState` for bound and unbound planning sessions rather than reconstructing coverage from presentation tables. Planned gear and reviewed planned skill/class sources use the same planning-coverage semantics as Coverage, including perfected-set family normalization such as `Perfected Roaring Opportunist` resolving through the reviewed `Roaring Opportunist` provider relationship; explicit primary/backup assignments remain raid-lead intent and count as planned coverage while proof strength stays separately visible. Duplicate effects, genuinely missing required effects, open player seats, and open gear decisions are derived from the state that Save will persist.
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
- **Comp Builder roster-first planning** keeps imported/selected groups at their real ESO size (4 or 12), shows Player from first paint with empty seats labeled `Recruit`, accepts **Load Team** directly on the page, treats Recruit as an open prescription slot that cannot borrow another player's saved build, scopes saved-build choices to the loaded player, and preserves known player/character identity when a build decision is still unresolved; the approved Phase 14 Work-chat shell is organized as **Raid Brief -> Recommended Team Plan + Why This Plan -> Team Health**, with Generate Team Plan as the dominant action and legacy matrix/evidence infrastructure kept behind the visible workflow; the Why This Plan recommendation and two alternative surfaces are selectable gear-choice cards that apply the chosen evidence-backed candidate to the highlighted chair, use only canonical five-piece set projections for those two-set packages, and expose confidence as a color-coded evidence state; the right-side gear picker can also select up to two individual five-piece sets across recommendation/alternative evidence, preserving that manual chair package into Raid Plan independently of any one observed two-set pairing; its Plan Name control is an editable saved-Raid-Plan picker, so selecting an existing plan loads it into Comp Maker while typing a new name creates a new Raid Plan on Save. Navigation into Comp Maker is plain navigation and never silently binds the page based on where the user came from. Generated Comp drafts remain composition evidence only and do not create or rename reusable Roster Team identities. The visible Comp Maker actions use **Load Players** for player/chair intake and **Auto-Fill Builds** for filling unresolved build/gear recommendations while preserving existing choices. The manual gear picker owns ordinary five-piece overrides only; Raid Plan handoff filters restored planned gear accordingly, and saving a manual five-piece choice preserves candidate monster/mythic/arena evidence instead of replacing the entire package. Phase 14 rebuild work now has a canonical typed **CompPlanState / CompChairState** boundary that round-trips through Raid Plan, preserves unrelated plan metadata/responsibilities, supports incomplete Recruit chairs, and persists per-chair Comp lock fields so user-fixed player/class/build/gear decisions survive save/reload. Raid Plan-bound Comp sessions now save this canonical state directly back to the originating Raid Plan without silently applying visible recommendations or routing through generated-roster draft persistence; the PLAN NAME picker and Raid Plan handoff both enter the same canonical state path. Comp Maker now participates in the app-wide unsaved-changes contract from canonical state: chair/context edits mark the plan dirty, Save persists canonical state, and Discard reloads the bound Raid Plan. Team Health is derived directly from canonical `CompPlanState`, including persisted planned gear and planned assignment intent, and separates open Recruit seats from unresolved gear gaps instead of treating every Recruit as ungeared.

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
\n\n## Raid Plan\- Raid Plan Coverage reconciles explicit buff/debuff ownership before generic provider availability: assigned providers are checked against saved-build and reviewed planned-set evidence, duplicate primary ownership is surfaced, and unassigned gaps remain visible without automatically moving support to a Tank or Healer.\nn\n- Saving a Raid Plan promotes any typed unknown gamertag into a minimal Personnel player record before stable identity resolution; it does not invent a character or build.\n- Team chairs use a neutral canonical skeleton: Tank 1/2, Healer 1/2, and DD 1–8. Empty chairs may persist class/build planning before a player is known; assigning a player fills the chair without changing its internal seat identity. Detailed raid duties such as Main Tank, Off Tank, kite, portal, tombs, add tank, and healer jobs remain separate Assignment-layer state rather than being encoded into the chair name.\n- The Team Class column uses the shared editable, case-insensitive contains autocomplete pattern over canonical ESO classes.\n- Trial-specific artwork banners appear in Raid Plan Selected Plan and Live Raid Current Encounter hero surfaces.\n\n\n## UI\n\n- Shared app page headers use the Collectibles-style uppercase Montserrat treatment with muted-gold text and restrained letter spacing; page-specific subtitles and context controls remain unchanged.

- **Rotation command-center visual contract** — Rotation Context stays on one compact row, intent tiles use restrained blue/silver hover/selected treatment, and generated results use the five-button icon navigator with a locked pre-generation state instead of exposed raw Qt tabs.

- **Raid Plan note** — the parchment Plan Note on Raid Plan Overview is editable and persists with the exact `RaidPlan` snapshot; loading another plan restores that plan's own note.
\n- **Rotation Builder Phase 14 shell** — Rotations are restored through an owned command-center page that preserves the current presentation while calling the existing generation and sustain engines directly; the legacy patched dashboard is not constructed at startup.\n
- Phase 14 Comp candidate provenance distinguishes **saved Builds** from **reference templates**: only real saved-build candidates may populate `selected_build_name`; reference templates keep source/candidate provenance and may contribute planned gear/class/Mundus without masquerading as an owned Build.
- Phase 14 saved Comp candidates carry stable canonical player, character, and build identity through the `PlayerBuild` compatibility snapshot. Duplicate-player prevention, provider-evidence recovery, saved-build binding, and provider-workload recovery use those stable IDs rather than treating display/source names as ownership.
- Phase 14 selected-chair Apply, Auto-Fill, and Team Health are canonical-state-only. `_comp_applied_candidates` remains a compatibility/presentation cache, while saved-player duplicate detection and applied-candidate recovery prefer `CompPlanState`.

- **OBS Field Note source overrides** — The Foundry dashboard Lua script exposes persistent OBS-side edit fields for `NOTE_Observation` and `FN_Location`. Blank values preserve the existing automatic JSON-driven text; entered values override the one-second overlay refresh safely.
