# Project Roadmap

**Project:** Black Feather Foundry  
**Last Updated:** 2026-08-03

---

# Vision

Build a reusable knowledge archive for The Elder Scrolls Online that powers the Composition Engine and future Foundry tools.

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

Build systems that consume the Archive.

Examples

- Buff analysis
- Build comparison
- Coverage analysis
- Recommendation engine
- Conflict detection
- Missing buff detection

---

# Phase 6 — User Interface

Replace development views with production tools.

Examples

- Archive browser
- Relationship explorer
- Validation dashboard
- Builder dashboard
- Search
- Data inspection

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

Current Priority

> Build clean Archive Records before expanding features.

Current Success Criteria

- Builders produce canonical records.
- Every entity has a permanent archive_no.
- Relationships are clean and validated.
- The Composition Engine consumes Archive data rather than raw source files.


---

# Parking Lot

Ideas worth keeping, but not currently being worked on.

- Add Antiquities
- Support multiple game versions
- Build encounter timeline visualization
- Search by mechanic
- Compare gear sets automatically