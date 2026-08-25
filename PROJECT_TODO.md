# FoundryDock Project TODO

## Immediate: Live Operations and Session Archive

- [X] Launch FoundryDock and confirm the local Python environment used to run
      the app is available. The checked-in `.venv` currently points to a
      missing Python executable.
- [X] Confirm **Start New Run** shows its warning and leaves the current run
      untouched when cancelled.
- [X] Confirm **Edit Timeline** opens the existing editor for a selected event
      and that Save persists the edited event.
- [X] Run an end-of-session check: save a Broadcast, save Field Notes,
      archive the Live Operations session, and confirm OBS plus the combined
      archive output.
- [ ] redo the layout like the live operation wireframe in the Docs folder
- [ ] make the new/save/archive/edit buttons much much larger

## Broadcast and Field Notes

- [X] Keep the established `CurrentBroadcast.json` workflow intact.
- [X] Do not rewrite the OBS Lua integration unless a real test shows it is
      broken.
- [X] Verify the resolved `CurrentBroadcastPath` before changing paths or Lua.
- [ ] a better save/button format so I know that I'm saving work to an archive
  
## Dashboard Page
- [ ] ??

## Raid Page
- [ ] ??

## Builds Page
- [ ] fix the team roster table so its not floating in that card 
- [ ]

## Capabilities Page
- [ ]

## Boss Page 
- [ ] set it up like the Boss mock up page

## Assignments Page 
- [ ]

## Optimization Page 
- [ ] fix table in Encounter Eval card so its not floating in the middle
- [ ] wire in rosters and players so I dont have to manually enter each time
- [ ] allow for more than 2 5-pc sets
- [ ] skill pulldown menu, why 4 of each skill? fix that
- [ ] only class skills

# Progression Page
- [ ]

## Reference page
- [ ] set is up like a mech reference page/boss page I want it to be am encyclopedia for mechs and named attacks


## Settings Page
- [ ] change the layout to match the settings wireframe in Docs
- [ ] add a way to disable pages or parts of the app



## Data and Optimizer Roadmap

- [ ] Finish the UESP importer and audit its coverage.
- [ ] Finish the ESO Wiki crawler and audit its coverage.
- [ ] Compare coverage and select a canonical source per entity/field.
- [ ] Normalize structured effects while retaining raw tooltip provenance.
- [ ] Cover DD needs: buffs, crit, sustain, weapon/spell damage, penetration,
      duration, uptime, conditions, targets, and proc requirements.
- [ ] Feed validated data into Build, Composition, and Optimizer work.

## Data Foundation

- [ ] Complete the Database Readiness Audit before running additional importers
      or redesigning the effect schema:
  - [ ] Inspect the current database schema.
  - [ ] Inventory populated tables and record counts.
  - [ ] Map existing tables to required application features.
  - [ ] Identify missing entities and columns.
  - [ ] Identify missing relationships.
  - [ ] Identify incomplete records and source-coverage gaps.
  - [ ] Only then select and run the required importers.
- [ ] Confirm canonical coverage for these entities: Skills, Skill Lines, Gear
      Sets, Potions, Capabilities, Encounters, and Mechanics.
- [ ] Confirm these relationships are represented and populated: Skill to
      Capability, Gear Set to Capability, Potion to Capability, Encounter to
      Mechanic, and Mechanic to Capability.
- [ ] Assess advanced effect data needed by the engine: capability and log
      aliases, conditional effects, values, durations, cooldowns, targets,
      boss armor, and penetration values.
- [ ] Complete the feature data matrix:
  - [ ] Builds: skills, morphs, and gear sets.
  - [ ] Composition: capabilities and relationships.
  - [ ] Recommendations: effect providers.
  - [ ] Penetration: armor and shred values.
  - [ ] ESO Logs: aliases and capabilities.
  - [ ] Trial planning: encounters and mechanics.
  - [ ] Statistics: confirm event data remains sufficient without additional
        database work.
- [ ] Re-crawl trial and dungeon data.
- [ ] Crawl Collections data and define how it connects to the app.
- [ ] Import glyph data into the database.
- [ ] Import armor traits into the database.
- [ ] Audit food and drink coverage in the database; import any missing buffs.
- [ ] Audit the existing trial, set, boss, skill, achievement, race, food, and
      potion importers; define a repeatable refresh workflow.
- [ ] Write parsers that derive structured effects from gear sets, skills,
      potions, food, and other raw tooltips.

## Product Navigation and UI

- [ ] Add a named-attack search experience.
- [ ] Make a player's build on the Roster page open that player's Build page.
- [ ] Audit the Capabilities page: clarify its purpose, identify missing
      behavior, and define its data source.
- [ ] Wireframe the remaining application pages.
- [ ] Add Foundry-style icons to navigation and appropriate UI surfaces.
- [ ] Connect Collections data to a usable Collections page.
- [ ] Connect Google Sheets to Achievement tracking.
- [ ] Ability to add multiple teams without adding miltiple roster names 

## Boss and Live Tools

- [ ] Create a Boss page with a mechanic timeline and tabs for mini-bosses and
      other trial bosses.
- [ ] Design an accessible boss-mechanic counter for Rylo:
  - [ ] Show mechanics and timing in a readable format.
  - [ ] Allow manual edits and personal notes.
  - [ ] Support use when visual AOE cues are unavailable.

## Composition Builder and Optimizer

- [ ] Create a team setup page for 12 players, names, and roles: 2 tanks,
      2 healers, and 8 damage dealers.
- [ ] Support multiple build profiles per player: General Population, Boss 1,
      Boss 2, and Boss 3.
- [ ] Add team metadata: team name, play times, and current goal.
- [ ] Calculate group buff coverage and identify missing buffs.
- [ ] Identify over-cap penetration and critical stats.
- [ ] Add optional recommendations for duplicated buffs, excessive caps, and
      better-fitting gear or skills.

## Completed

- [x] Complete a cleanup and packaging-readiness audit.
- [x] Consolidate project TODO lists.
- [x] Make Champion Point changes persist while browsing.
- [x] Restore the Live Operations footer Save action.

## Guardrails

- [ ] Protect `ui/builds_page.py`, `widgets/builds*`, and theme/component work
      during Live Operations and OBS restoration.
- [ ] Do not remove archive functionality or planned composition-engine files.
- [ ] Do not force-add ignored `.db` files.
- [ ] Stage only deliberately reviewed files; avoid `git add .` while unrelated
      work remains in the tree.
