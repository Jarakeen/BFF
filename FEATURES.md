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
- Multiple visual themes
- Theme-aware UI components
- Rylo theme and Rylo-specific visual assets
- Theme-aware cards, controls, tables, and result surfaces
- Raid Engine overview accents and New Build entry adapt to Foundry teal/amber or Rylo's squared steel palette, with text and numeric progress cues alongside color
- Raid Engine overview cards reflow into fewer columns when the available desktop width is narrow
- Main and Coverage share canonical saved-build effect evidence: available static sources, conditional sources, effects not identified, and unmapped or unaudited effects remain distinct; Coverage filters work without inferring assignments or uptime
- Raid Engine dashboard sends explicit Team Optimization slot/build selections into a labeled Coverage scope; Coverage can switch between that team snapshot and all saved builds without inferring provider assignments
- Raid Engine dashboard summarizes static coverage evidence with distinct available, conditional, not-identified, and unverified labels rather than treating an unknown effect as missing
- Empty boss, mechanic, positioning, and Raid Map panels use distinct compact field-art placeholders for Foundry and Rylo, with visible labels that distinguish decorative art from reviewed encounter evidence
- Main character overview dashboard
- Role-aware application surfaces
- Archive page / archived data access

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
- Build comparison
- Build performance information
- Save generated or modified builds for later reuse

---

## Build Import

- Screenshot-based build import
- OCR-assisted build import from ESO screenshots
- Screenshot recognition support for build fields
- Import review before applying detected build information
- Achievement progress import

---

## Exports & Sharing

- CSV exports
- Custom themed CSV exports
- Theme-aware export presentation
- Build / analysis data export workflows
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
- Ready checkbox on each saved build, shown on the Raid Engine Overview
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
- Mundus / food / potion configuration
- Scribed Skills interface
- Build-specific performance information
- Role-aware build information

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
- Skills to Work On recommendations
- Performance history / comparison surfaces
- Build-linked performance context

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

- Player roster
- Character roster records
- Role assignment
- Build assignment
- Multiple builds associated with roster characters
- Load roster players into team workflows
- Preserve roster identity separately from build identity
- Save generated team builds back to roster characters

---

## Comp Maker / Team Builder

- Build a raid team for a selected trial
- Start from one or more known characters and fill remaining positions
- Recruit-slot workflow
- Tank / healer / Damage Dealer role handling
- Role autofill
- Candidate pool generation
- Candidate ranking
- Candidate application
- Provider coverage analysis
- Team prescription generation
- Team prescription preview
- Team optimization pipeline
- Load Team from Roster
- Generate Team / automatic raid composition construction
- Trial-specific composition planning
- Compare two team compositions
- Compare projected team damage ceilings
- Explain why one composition is preferred
- Identify missing or redundant team support
- Inject required gear sets or support capabilities into candidate builds
- Preserve healer / tank / Damage Dealer role boundaries during optimization
- Saved-build candidate evaluation
- Provider workload analysis
- Provider workload frontier analysis
- Rotation-aware provider workload analysis

---

## Team Optimization

- Optimize an existing roster-derived team
- Trial-specific optimization
- Encounter-specific optimization inputs
- Build candidate ranking
- Provider assignment optimization
- Support-set allocation
- Buff / debuff coverage evaluation
- Duplicate-provider detection
- Missing-provider detection
- Sustain-aware candidate evaluation
- Damage-ceiling comparison
- Explainable optimization results
- Candidate build modification / injection
- Preview optimization changes before applying them

---

## Rotation Builder

- Generate combat rotations
- Live canonical Generate context is resolved from the current saved build and selected encounter at click time rather than being frozen when the page opens
- Explicit canonical recovery resource selection for Magicka or Stamina
- Explicit canonical recovery-trigger percentage with no assumed default threshold
- Canonical saved-build static context supplies the selected recovery pool maximum instead of a UI placeholder value
- Missing encounter demand policy blocks encounter-aware Generate unless reviewed policy or an explicitly reviewed empty policy is configured
- Generate-time candidate evaluator and final scorecard resolvers are composed from the exact generated seed plan through canonical sustain, duration, scorecard, and ranking services
- Role-aware rotation construction
- Healer rotation construction
- Shared canonical multi-demand healer role-output composition for audits and production callers
- Generate-time healer role evidence from the selected saved build and canonical healing-demand bundle
- Verified healer demand criteria retained as Generate-time hard obligations
- Demand-window scoping for externally triggered healer effects
- Explicit-attacker Minor Lifesteal demand projection
- Read-only Minor Lifesteal runtime evidence discovery from ESO Logs
- Tank rotation support
- Damage Dealer rotation support
- Candidate skill generation
- Candidate skill ranking
- Skill-family matching
- Canonical skill identity matching
- Encounter obligation integration
- Buff / debuff obligation scheduling
- Provider assignment integration
- Potion cadence handling
- Potion cooldown handling
- Resource / sustain awareness
- Class-passive awareness
- Armor-passive awareness
- Gear-bonus awareness
- Effect-duration modification awareness
- Rotation timing adjustment for sets that extend effects
- Major / Minor effect coverage awareness
- Ability-family reconciliation for ESO Logs data
- Rotation workload evaluation
- Canonical whole-plan candidate evidence across sustain, duration, and provider workload
- Provider primary-role displacement evidence retained without inventing missing workload values
- Rotation candidate explanations
- Encounter-specific rotation construction
- Selected encounter content type automatically feeds role-aware gameplay policy when no explicit override is supplied
- Configured authoritative plan evidence composes Generate-action role evidence without inferring healer reliability or assignment exceptions
- Canonical workload evaluation
- Workload frontier comparison

---

## Extreme Build Engine

- Extreme build optimization
- Push a selected stat / outcome toward its theoretical practical maximum
- Extreme healing optimization
- Actual-heal optimization
- Class-route candidate evaluation
- Skill candidate evaluation
- Gear candidate evaluation
- Mundus evaluation
- Critical-healing calculations
- Conditional healing optimization
- Build comparison for extreme outcomes
- Read-only optimization audits against canonical game data
- Explain the sources of an extreme result rather than returning only a number

---

## Combat Math

- Deterministic static combat calculation
- Database-driven skill coefficients
- Max-resource scaling
- Weapon / Spell Damage scaling
- Separate attacker Damage Done stage
- Critical eligibility and expected-critical handling
- Critical resistance handling
- Resistance and penetration mitigation
- Target Damage Taken stage
- Final damage calculation
- Healing calculations
- Critical healing calculations
- Resource / sustain calculations
- Ability-cost handling
- Recovery timing
- Temporary recovery modifiers
- Explicit resource restoration events
- Resource timeline projection
- Sustain failure detection
- Sustain shortfall reporting
- Ending-resource margin reporting
- Explicit handling of unsupported / unresolved mechanics instead of silently treating them as zero

---

## Effects & Buff / Debuff System

- Canonical effect architecture
- Effect variants
- Effect magnitude
- Effect duration
- Effect chance
- Effect cooldown
- Effect trigger
- Effect target
- Effect conditions
- Effect stacking rules
- Build effect resolution
- Skill-derived effects
- Gear-derived effects
- Consumable-derived effects
- Major / Minor effect handling
- Conditional effect handling
- Temporal effect activation
- Effect-duration extension from gear and other modifiers
- Provider coverage analysis
- Effect-source explanations

---

## Encounter System

- Canonical encounter records
- Trial encounter data
- Boss / parent-content relationships
- Encounter evidence records
- Encounter mechanic evidence
- Encounter phase support
- Encounter projection
- Encounter repository
- Encounter health / completeness audits
- Encounter mechanic gap audits
- Explicit unresolved encounter evidence
- Trial-specific optimization context
- Encounter-specific provider obligations
- Encounter-specific rotation obligations
- Add-pull / non-boss encounter support
- Reviewed encounter-evidence projection supplies boss-guide timeline fallback when canonical phase rows are absent
- Encounters planning page replaces canned example timelines/mechanics with the selected boss's canonical-or-reviewed timeline, searchable mechanic strategy, common raid names, mitigation guidance, and quick raid-lead callouts
- Encounters Overview projects the selected fight's reviewed timeline, mechanic handling, raid-lead callouts, and evidence status while keeping unreviewed packet aliases hidden
- Encounter guide coverage audit reports bosses missing effective timelines or reviewed strategy so research can be queued systematically

---

## Raid Maps & Encounter Visualization

- Raid map support
- Empty Raid Map and positioning previews show clearly labeled decorative placeholders until a real map or captured positioning is available
- Animated raid maps
- Encounter-position visualization
- Mechanic-position visualization
- Player / role assignment visualization
- Movement-path visualization
- Mechanic timing visualization
- Trial-specific map data
- Visual encounter planning rather than text-only assignments

---

## Achievements

- Achievement database / reference data
- Achievement tracking
- Achievement progress import
- Achievement progress display
- Achievement detail pages
- Achievement broadcast page
- Achievement desk / work surface
- Suggestions for achievements close to completion
- Trial achievement support
- Completion / progress indicators

---

## Collectibles / Sticker Book

- Collectibles database / reference data
- Sticker Book page
- Owned / missing collectible tracking
- Checkbox-based collectible tracking
- Collection progress display
- Missing-item views
- Compact multi-column collection layouts
- Suggested collectibles to work on
- Optional collectible thumbnail support

---

## Gear Tools

- Gear-set database
- Gear-set effects
- Traits and enchantments
- Bookmarked gear
- Gear candidate evaluation
- Gear-set injection into optimization candidates
- Support-set coverage analysis
- Set-duration and set-effect awareness in combat / rotation logic
- Sticker-book / collection relationships where applicable

---

## Skills & Progression

- Skill database
- Skill ranks
- Morphs
- Passives
- Skill coefficient data
- Owned skill lines
- Passive-rank persistence
- Character-level progression
- Skill-bar configuration
- Scribed Skills
- Bulk progression purchasing controls
- Canonical lower-snake-case skill identity used where ESO numeric ability IDs are unstable or context-dependent

---

## Champion Points

- Champion Point configuration
- Champion Point cards / grouped UI
- Champion Point ownership / selection controls
- Bulk **Buy All** progression control
- CP information retained with builds
- Explicit unresolved handling where a CP mechanic is not yet modeled

---

## Data & Imports

- Local ESO SQLite database
- Database-backed skills
- Database-backed morphs
- Database-backed skill ranks
- Database-backed skill coefficients
- Database-backed gear
- Database-backed set effects
- Database-backed provisioning data
- Database-backed Mundus data
- Database-backed encounter information
- UESP-derived imports
- ESOUI-derived information where appropriate
- ESO Logs-derived analysis / validation data
- Encounter evidence corpus
- Import provenance
- Canonical vs. source/raw data separation
- Data coverage audits
- Missing / unresolved data reporting

---

## ESO Logs / Real Combat Validation

- ESO Logs data ingestion / matching workflows
- Ability-family matching across log IDs
- Canonical skill reconciliation
- Real combat evidence used to validate modeled behavior
- Performance analysis based on log-derived data
- Encounter mechanic validation against observed combat
- Provider / effect uptime analysis
- Rotation evidence analysis

---

## Broadcast / Streaming Tools

- Broadcast module
- Achievement broadcast page
- Stream / broadcast-oriented app surfaces
- OBS-related integration support
- Stream event support
- Executable packaging with the Broadcast module optionally excluded

---

## Trial / Raid Utility Tools

- Raid schedule support
- Encounter assignments
- Trial-specific team planning
- Trial-specific build planning
- Trial-specific rotation planning
- Trial-specific optimization
- Animated raid maps
- Asylum Sanctorium Perfecta timer / utility page
- Encounter evidence and mechanic reference tools

---

## Explainability & Auditing

- Explain why a build candidate ranked above another
- Explain why a team composition was selected
- Explain provider coverage decisions
- Explain workload decisions
- Explain combat-math stages
- Explain sustain failures
- Preserve unsupported / unknown mechanics explicitly
- Read-only audits
- Encounter data audits
- Canonical-gap audits
- Data provenance
- Regression tests tied to real production paths

---

## Quality-of-Life Features

- Bulk **Buy All** controls
- Saved builds
- Saved roster characters
- Load Team from Roster
- Bookmarked gear
- Achievement suggestions
- Collectible suggestions
- Role-aware screens
- Theme-aware presentation
- Compact card layouts
- Search / selection surfaces across build and game-data tools

---

## Things Worth Remembering

These are easy to lose in the size of the project because they are not necessarily entire pages of their own.

- A build can be imported from screenshots using OCR assistance.
- CSV exports can use custom BFF themes instead of being generic raw tables.
- Raid maps can be animated.
- Team construction can reason about builds, roles, providers, support coverage, and encounter needs rather than only arranging names in slots.
- Rotation construction can account for class passives, armor bonuses, potion cadence, encounter obligations, and gear that changes effect duration.
- Optimization is designed to explain **why** a candidate is better, not merely output a winner.
- Character identity, roster identity, and build identity are deliberately separate concepts.
- Combat math keeps unsupported mechanics explicit instead of quietly converting uncertainty into zero.
- ESO numeric ability IDs are not treated as stable canonical skill identity when context-dependent IDs would make the data unreliable.
- The app contains both player-facing tools and research / audit surfaces used to verify the underlying ESO model.
- Combat Reference exposes gameplay-practice rules, canonical encounter mechanics, canonical combat effects, versioned Major / Minor named-effect semantics, reviewed ability / gear / potion providers, reviewed research enrichment, player-facing common names, mitigation guidance, provenance, death-review guidance, and downstream FoundryDock consumers in one human-readable surface.
- Encounters can reuse reviewed encounter evidence as a strategy/timeline fallback while preserving canonical boss-guide phases as the higher-authority source.

---

## Maintenance Rule

Add an entry when we build something that is:

1. directly usable in the app;
2. a meaningful workflow improvement;
3. a notable analysis / optimization capability;
4. an import, export, visualization, automation, or integration worth remembering; or
5. sufficiently unusual that six months from now one of us is likely to rediscover it and say, “wait, we already built that?”

Keep entries short. Put implementation detail, test evidence, completion criteria, and future plans in their appropriate technical documents rather than turning this index into another roadmap.
