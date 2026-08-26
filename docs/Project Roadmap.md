# Project Roadmap

**Project:** Black Feather Foundry  
**Last Updated:** 2026-08-26

---

# Vision

Build a reusable knowledge archive for The Elder Scrolls Online that powers the Roster composition system and future Foundry tools.

The project is organized into milestones rather than release dates.

---

# Phase 1 — Foundation

**Goal:** Establish the architecture and standards.

## Complete

- [x] Project structure
- [x] Archive Record Standard
- [x] Archive Design Principles
- [x] Data Pipeline
- [x] Relationship Types
- [x] Initial Buff Builder
- [x] Initial Debuff Builder

## Remaining

- [ ] Archive Registry
- [ ] Relationship Builder
- [ ] Validation system

---

# Phase 2 — Archive

**Goal:** Build complete canonical datasets.

## Combat

- [ ] Buffs
- [ ] Debuffs
- [ ] Status Effects

## Skills

- [ ] Skills
- [ ] Skill Lines
- [ ] Morphs

## Equipment

- [ ] Gear Sets
- [ ] Mythics
- [ ] Arena Weapons
- [ ] Monster Sets

## Build

- [ ] Champion Stars
- [ ] Mundus Stones
- [ ] Foods
- [ ] Drinks
- [ ] Potions
- [ ] Poisons

## Content

- [ ] Trials
- [ ] Dungeons
- [ ] Arenas
- [ ] Zones

## Encounters

- [ ] Bosses
- [ ] Mechanics
- [ ] Encounter Phases

## Progression

- [ ] Achievements
- [ ] Collectibles

---

# Phase 3 — Relationships

**Goal:** Connect Archive Records.

Examples

- Gear Sets grant Buffs
- Skills apply Buffs
- Bosses use Mechanics
- Dungeons contain Bosses
- Achievements unlock Collectibles

---

# Phase 4 — Validation

Build automated validation tools.

Examples

- Duplicate IDs
- Missing fields
- Missing archive_no
- Broken relationships
- Duplicate concepts
- Invalid references

---

# Phase 5 — Composition Engine

**Status: Complete**

**Goal:** Build systems that consume the Archive and produce an authoritative roster/encounter composition result.

Completed capabilities:

- [x] Character/build capability resolution
- [x] Roster capability resolution
- [x] Buff and debuff coverage analysis
- [x] Missing capability detection
- [x] Insufficient coverage detection
- [x] Redundancy and resilience classification
- [x] Provider conflict detection
- [x] Encounter requirement activation by condition
- [x] Encounter-level evaluation
- [x] Typed recommendation intents
- [x] Resolved-build capability comparison
- [x] Production roster composition orchestration

Phase 5 deliberately stops before choosing a specific replacement build or optimizing provider assignments. Those decisions consume the Phase 5 result and belong to later Roster/Optimization work.

---

# Phase 6 — User Interface

**Status: Current**

**Goal:** Replace development views with production tools that expose the completed composition engine clearly.

Planned areas:

- [ ] Archive browser
- [ ] Relationship explorer
- [ ] Validation dashboard
- [ ] Builder dashboard
- [ ] Search
- [ ] Data inspection
- [ ] Production Roster/encounter workflows
- [ ] Coverage dashboard
- [ ] Assignment workspace
- [ ] Optimization workspace
- [ ] Performance/ESO Logs views

---

# Future Ideas

Ideas that are intentionally deferred.

- Localization
- Patch history
- Version comparisons
- Build templates
- Encounter planner
- Group composition planner
- AI-assisted search
- Export tools

---

# Current Focus

> Build the production Roster workflows on top of the completed Composition Engine.

Current success criteria for Phase 5 are satisfied when:

- Builders produce canonical records.
- Every entity has a permanent archive_no.
- Relationships are clean and validated.
- The Composition Engine consumes resolved Archive data rather than raw source files.
- A roster can be evaluated against encounter requirements.
- Coverage gaps, conflicts, and recommendation intents are returned as typed data.

---

# Parking Lot

Ideas worth keeping, but not currently being worked on.

- Add Antiquities
- Support multiple game versions
- Build encounter timeline visualization
- Search by mechanic
- Compare gear sets automatically
