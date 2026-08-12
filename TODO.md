## Bugs 
- [ ] main_window.py    line 462   lambda checked=False, page=page: self._select_page(page)
                        line 505   in _select_pageself.refresh_top_bar_summary()       ^^^^^^^^^^^^^^^^^^^^^^^
                        line 2356, in refresh_top_bar_summary self.top_bar_expedition_label.       setText        (self   _broadcast_location_text() or "—") 
                        AttributeError: 'MainWindow' object has no attribute 'top_bar_expedition_label'
- [X] desktop_gui.py    Import "customtkinter" could not be resolved
- [ ] main.py           Import "fastapi" could not be resolved
                        Import "pydantic" could not be resolved
                        Import "fastapi" could not be resolved

# FoundryDock Roadmap
- [ ] live operations - be able to edit a boss wipe pull timestamp in case I mess up the percentage
- [ ] how am I saving this to the over all archive for the run? there is no way these are all getting tied together
- [ ] a way to export the archived notes to something pretty


Phase 1 – Operational MVP

Mission: Complete one expedition from planning to archive without ever leaving the Foundry.

🔥 Epic 1 — Shared Application Framework

These improvements affect the entire application.

Navigation
- [x]  Group sidebar into logical sections (CURRENT SESSION/STREAM OPERATIONS/RECORDS/PROJECTS/SYSTEM headings with dividers, matching your sketch. Caught a real bug while building it: the active-page highlight logic assumed button list position matched page index directly - reordering buttons into sections broke that assumption, since Incident Report (page 4) now visually comes before Archive Log (page 3). Fixed by tracking each button'''s actual page index explicitly instead of relying on position, and verified with a standalone test that selecting page 3 vs 4 highlights the correct button.)
                        BLACK FEATHER
                        FOUNDRY
                        FIELD OFFICE

                        CURRENT SESSION
                        ────────────────
                        • Broadcast Desk
                        • Field Office

                        STREAM OPERATIONS
                        ────────────────
                        • Stream Events

                        RECORDS
                        ────────────────
                        • Incident Reports
                        • Archive Log

                        PROJECTS
                        ────────────────
                        • Achievement Run
                        • Collections

                        SYSTEM
                        ────────────────
                        • Settings
- [x]  Highlight active page (part of the sidebar grouping work - buttons now track their own page index directly)
- [x]  Standardize page titles and subtitles (the subtitle label existed already but was hardcoded to one static string that never changed between pages - now it updates per page using your exact text, uppercased to match the rest of the app's styling. Also added the missing QLabel#pageSubtitle stylesheet rule since it had none at all before.)
- [ ]  Standardize page headers
- [ ]  Standardize action footer
- [ ]  Add page/report serial number to every workspace
- [x]  I want the sidebar buttons bronze as well (nav button text now uses the bronze accent color instead of plain light text)

UI Consistency
- [ ]  Consistent button sizing (archive log - 3 buttons across)
- [ ]  Consistent spacing and margins
- [ ]  Better empty-state messages
- [ ]  Tooltips on all action buttons
- [x]  Fix the logo so it fits inside that space (the brand mark/title/subtitle had dedicated size tokens already defined in Metrics - BRAND_MARK_SIZE, BRAND_TITLE_SIZE, BRAND_SUBTITLE_SIZE - they just were never wired into the stylesheet, so everything was falling back to the tiny default body text size. Wired them in properly.)
- [X]  Fix check boxes so they show a checked box with the bronze color when checked
- [x]  Consolidate the two themes qss and theme/metrics/color that are both competing rn (deleted theme.qss entirely - it was a third, fully independent source of truth with 45 hardcoded hex colors and a 4th font family, completely disconnected from Colors/Fonts. Retired theme.py too - its useful bits, the roles bundling, folded into theme_manager.py. Fixed a naming collision where theme.py and theme_manager.py both defined a class called Theme. ThemeManager now exposes theme.colors/theme.fonts/theme.metrics/theme.roles as full namespaces, plus keeps the original 5 convenience properties so nothing broke. Adopted the new dark/brass palette to match the newer mockups and enriched the actual applied stylesheet to use it.)
- [ ]  Theme system (Phase 1 foundation)

Shared Expedition Data
- [x]  Expedition (now reads from Broadcast Desk's Location/Content field)
- [x]  Objective (now reads from Broadcast Desk's Tonight's Goal field)
- [x]  Difficulty (new Normal/Veteran/Hardmode checkboxes added to Broadcast Desk)
- [x]  Location (same field as Expedition above)
- [x]  Weather (moved from Field Office to Broadcast Desk)
- [x]  Coffee (moved from Field Office to Broadcast Desk)
- [x]  Coffee Level (moved from Field Office to Broadcast Desk, randomize button came with it)
- [x]  Engineering (moved from Field Office to Broadcast Desk)
- [x]  Incident Number (moved from Field Office to Broadcast Desk)
- [ ]  Current Archive ID (not yet - needs its own design pass)

Broadcast Desk becomes the source. Everything else reads from it. (Field Office now shows all 8 of these as a read-only summary panel, refreshed live whenever you switch to that tab. Field Office's own Clear button only clears its own fields now (Assignment/Observation/Context/Recommendations/status checkboxes) - it no longer wipes the shared Broadcast Desk data. Save to OBS/Save to Archive on Broadcast Desk now include all these fields too.)

🎙 Epic 2 — Operations
Broadcast Desk
- [ ]  Start Stream/Archive Timer
        moss green button on far right lower side of broadcast screen 
- [ ]  Display Expedition ID
- [ ]  Better validation
- [ ]  Save draft
- [ ]  Load draft
- [ ]  Character counter
- [ ]  Preview before OBS

Field Office - Simplify
- [X]  Remove duplicated fields (objective, expedition, difficulty, location)
- [X]  Read Expedition from Broadcast Desk
- [X]  Read Objective from Broadcast Desk
- [ ]  Read Difficulty from checkboxes
- [ ]  Save observations
- [ ]  Load observations
- [ ]  Search notes
- [ ]  Observation templates
- [ ]  Timestamp option
- [ ]  Tagging

Stream Events
- [ ]  Boss percentage tracker
- [ ]  Boss mechanic tracker
- [ ]  Better timeline events
- [?]  Narration preview
- [ ]  Recently used narration
- [ ]  OBS scene verification
- [ ]  Test OBS button

📁 Epic 3 — Archive

Archive Browser
- [x]  Display archive serial number
- [x]  Open archive by serial (click any archive in the list to load its full report in the Selected Archive panel)
- [x]  Search archives (matches against the full archive text, so boss names/dungeon/trial/location/serial/date all work - not just a dedicated field per category)
- [ ]  Filter by Boss/Dungeon/Trial/Expedition/Earth Date/Tamriel Date/Favorite (single search box handles most of this; dedicated category filters and Favorites not built yet)

Archive Viewer - Display:
- [ ]  Mission Summary
- [ ]  Marker Log
- [ ]  Boss Log
- [ ]  Field Notes
- [ ]  Incident Reports
- [ ]  Achievements
- [ ]  Collections Earned
- [ ]  Lessons Learned
- [ ]  Stream Summary

Archive Metadata
✅ Earth Date
✅ Earth Time
✅ Timezone
- [ ]  OBS Start Time
- [ ]  Stream Duration
- [ ]  Twitch VOD - box to enter and store and then see later
- [ ]  YouTube Link - box to enter and store and then see later
- [ ]  Timeline events
- [ ]  Expedition ID
- [ ]  Remove Tamriel year until the game advances

Archive Linking
- [ ]  Link Incident Reports
- [ ]  Link Field Notes
- [ ]  Link Achievement Runs
- [ ]  Link Collections
- [ ]  Link Stream Events

Archive Statistics
- [ ]  Total expeditions
- [ ]  Boss clears
- [ ]  Pull count
- [ ]  Wipes
- [ ]  Achievement attempts

📄 Epic 4 — Incident Reports
- [ ]  Number reports using Tamriel format
- [ ]  Search reports
- [ ]  Load reports
- [ ]  Archive reports
- [ ]  Link reports to expedition
- [ ]  Daily incident counter

🏆 Epic 5 — Achievement Center
Backend
- [ ]  Google Cloud project
- [ ]  Service Account
- [ ]  Google Sheets connection

UI
- [ ]  Achievement browser
- [ ]  Tree view
- [ ]  ESO category layout
- [ ]  Search
- [ ]  Easier form using ESOAchievement50.php

During Run
- [ ]  Live checklist
- [ ]  Progress tracking
- [ ]  Notes

Archive Integration
- [ ]  Archive completed achievements
- [ ]  Achievement history
- [ ]  Success rate

📦 Epic 6 — Collections
Collection Types
- [ ]  Mounts
- [ ]  Pets
- [ ]  Motifs
- [ ]  Furnishings
- [ ]  Recipes
- [ ]  Titles
- [ ]  Costumes
- [ ]  Skins
- [ ]  Personalities
- [ ]  Houses
- [ ]  Antiquities
- [ ]  Books

Statistics
- [ ]  Overall completion
- [ ]  Missing collectibles
- [ ]  Recently earned
- [ ]  Filters
- [ ]  Search

⚙ Epic 7 — Shared Services
- [ ]  Unified notification system
- [ ]  Shared save/load dialogs
- [ ]  Shared file picker
- [ ]  Central error handler
- [ ]  Logging improvements
- [ ]  Archive hotkey
- [ ]  Archive + timestamp hotkey

📖 Epic 8 — Documentation
- [ ]  Vision.md
- [ ]  Workflow.md
- [X]  Modules.md
- [X]  Roadmap.md
- [ ]  DataFlow.md
- [ ]  Changelog.md
- [X]  TODO.md

🔬 Research / Design
- [ ]  OBS Dock support
- [ ]  Documentary narrator audio
- [ ]  Boss mechanics workspace for YouTube guides
- [ ]  Archive numbering strategy review
- [ ]  Achievement Run prefix (AC? AR?)
- [ ]  UI theme system expansion

🚧 Phase 2 (Do Not Build Yet)
Boss Console, Composition Builder, ESO Data Engine, Reference Library, Advanced archive search, Timeline visualization, Plugin system, Guild statistics, AI-assisted summaries

✅ Completed
✅ Archive numbering
✅ Archive save workflow
✅ Clear archive display
✅ Refresh button relocation
✅ Automatic Earth Date
✅ Automatic Earth Time
✅ Timezone recording
✅ Settings-driven archive path

🎯 Phase 1 Definition of Done
A complete expedition can be managed entirely inside the Foundry: create it in Broadcast Desk, record observations in Field Office, track events in Stream Events, log incidents as they happen, track achievement objectives, record newly earned collectibles, finalize and save a complete archive, reopen that archive months later and understand exactly what happened.


## Odds & Ends / BFF Achievement Tracker - Progress
- [ ] Still needed from you: Google Cloud project + Service Account + share the sheet with it (I'll walk through this step by step)
- [ ] Still needed: build the actual Odds & Ends browsing UI (achievement tree matching the game's categories) that calls into this service
- [ ] Mounts/Motifs/Recipes/Furnishings tabs - different layouts, not yet scoped (achievement tabs only for this pass)
- [ ] here is a list of all of the achievements https://esoitem.uesp.net/viewlog.php?record=achievements
- [ ] here is a list of achievment categories https://esoitem.uesp.net/viewlog.php?record=achievementCategories
- [ ] here is a list of all collectables https://esoitem.uesp.net/viewlog.php?record=collectibles 
- [ ] here are all the books https://esoitem.uesp.net/viewlog.php?record=book


## Questions
- [?] AC file prefix for Achievement runs ? or did we make something else?
- [ ] can we put the app in a dock in OBS?
- [?] Hotkey the archiving? Archive and clear? Archive and mark time into stream without having to record? 
- [?] the fonts on my cards dont look great. Do you have any suggestions?


## General
- [ ] I want the date on Clipboard to display in OBS as just date and month in Tamriel time
- [ ] I want to denote the file number at the top of each tab like the Achievement Run tab has that displays the current report number I'm working on.
- [ ] daily incidents number incrimenter for TOP bar in OBS
- [ ] use the ESOAchievement50.php file to make the Achievement form easier to fill out  
- [?] play an audio track alongside the Natural History Narrator notes - like a documentary narrator reading them aloud. I have Audio files in folders that match the notes headings with names that are similar. But I can rename as needed.
- [ ] I'm having an idea, I want to talk thru this on this page right here. lol My BFF and I are going to work on dungeon Perf videos for youtube and we need to track mechs for each boss to explain them well in the videos. I think I need a page, or a a way to tweak Stream Events so I can better track Boss percentages and mechs.
- [ ] I'm also playing with the idea of making this app having UI themes so I can change the look
- [ ] add a way to add team names in the setting so its faster to add them in Broadcast Page

## Broadcast Desk
- [ ] I want a way to start off the Archive Log stream timer and this feels like the right place to do it. Maybe add a small button to Start the Stream in Archive Log. 

## Field Office
- [ ] I think I want to reduce some redundant 'boxes'. How many instances of the same end value can we consolidate? I'm thinking we can move Weather, Coffee, Coffee Level, Engineering, and Incident Number to Broadacast page. And use the value from Broadcast page Location/Content for Expedition. And use Tonights Goal for Objective. Then we can add check boxes for Difficulty - Normal, Veteran, Hardmode - and that value can go into the Difficulty spot. Put those in the Tonights Briefing area. 

## Stream Events


## Achievement Run Tracker

## Archive Log Page
- [x] show me which logs I'm looking at by serial number (Archive Browser list shows serial + date + location + event count for every past archive)
- [x] let me pull up logs by number (click any entry in the Archive Browser list)
- [x] later let me search by like boss name or dungeon/trial/location/serial number/earth date
- [x] rn Archive Log is constantly showing the info from one of the logs. Can we have it default to blank please (Marker Log/Boss Log now start blank with a placeholder until you click Refresh)

## Time Archive
- [ ] OBS session start time
- [ ] Stream duration
- [ ] Twitch VOD link
- [ ] YouTube video link
- [ ] Automatic Expedition ID
- [ ] Timeline event logging
- [ ] Cross-link Incident Reports ↔ Field Notes ↔ Expedition
- [ ] Generate Stream Summary
- [ ] can we take the title I choose and add it to the Incident Reports ↔ Field Notes ↔ Expedition md? What are some options that make that possible?
- [ ] until ZoS advances the year in Tamrial, remove the year from the date field.
- [ ] I want to start numbering the reports for better tracking in a specific way. On 'client side' by Tamriel Month and Day (XX-MMDD-###) example IR-SH23-02. But on back end please keep earth time & dates.
        use these abbreviations for the months: MS  Morning Star, SD  Sun's Dawn, FS  First Seed, RH  Rain's Hand, SS  Second Seed, MY  Mid Year, SH  Sun's Height, LS  Last Seed, HF  Hearthfire, FF  Frostfall, SU  Sun's Dusk, ES  Evening Star

- [ ] on Settings page make the file input boxes into file choosing buttons
- [ ] broadcast desk bottom section, a horizontal area of "green lights" for before streaming checklist. Titles/Notifications, OBS, Elgato, Audio, 
