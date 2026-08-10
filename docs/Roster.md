Claude Prompt: Foundry Roster Page

I want you to build a new Roster page for Black Feather Foundry.

The purpose of this page is to maintain an ESO raid-team roster that will eventually feed an engine that optimizes raid teams.

First: inspect the existing project

Before writing code, inspect the existing repository and identify:

The current page architecture
FoundryPage
Existing page/layout components
FoundryCard
FoundryHeader
Existing action/status bar patterns
services/eso_database.py
Existing SQLite schema/importer patterns
Existing models
Existing settings architecture
Any existing roster/team-related code
Any TODO/vision documents describing the Console or raid optimizer

Do not create a second database connection layer.

Use the existing:

services.eso_database.EsoDatabase

and the existing data/eso.db.

Follow the project's existing architecture and naming conventions.

Roster Page Concept

Create:

ui/roster_page.py

and whatever supporting model/widget/service files are appropriate.

The page should be designed as the roster management interface, not the optimizer itself.

The optimizer will come later.

The page should allow me to maintain players and their ESO roles/character information in a structured way.

Roster UI

I want the page to feel like the rest of Black Feather Foundry:

dark
restrained
bronze/chocolate accents
compact
readable
field/archive aesthetic
not giant modern web-app controls
don't waste vertical space

Use existing Foundry components wherever possible.

Header

Use:

Roster
Maintain expedition personnel and their capabilities.

or an equivalent Foundry-style subtitle.

Main Layout

Use a two-column layout.

Left: Roster

A compact table/list showing current roster members.

Columns should include approximately:

Player
Character
Class
Role
Primary Role
Secondary Role
Status

The exact columns should be adapted to the existing project architecture if appropriate.

The roster should be compact enough that a full 12-person ESO trial roster can be viewed without ridiculous scrolling.

Right: Personnel Record

When a roster member is selected, show an editable personnel record.

At minimum include:

Identity
Player Name
Character Name
ESO Class
Roles

Support:

Tank
Healer
Damage Dealer

Allow primary and secondary role designation.

Availability / Status

Include a simple status such as:

Active
Bench
Inactive

Do not overcomplicate this yet.

ESO-Specific Information

Design the model so we can eventually add:

Class
Role
Primary Role
Secondary Role
Preferred Role
Gear
Sets
Build
Skills
Experience
Trial Experience
Hard Mode Experience
Perfecta/achievement progress

Do not attempt to implement all of those unless the existing project already supports them.

For now, build the structure so they can be added without rewriting the roster system.

Database

The page should be wired to the existing SQLite database if practical.

Do not create a separate roster database.

Use:

data/eso.db

through:

services.eso_database.EsoDatabase

If the database does not currently have roster tables, create a clean schema for them.

Prefer something like:

roster_member

with fields appropriate for the current UI.

Do NOT put everything into one giant JSON blob.

Use normalized relational data where appropriate.

For example, roles/status should be structured fields rather than an arbitrary JSON object.

Important Architecture Rule

Separate these concerns:

UI
 ↓
Roster model/service
 ↓
EsoDatabase
 ↓
SQLite

Do not put SQL directly throughout the Qt widgets.

The page should be able to load/save roster records through a model/service layer.

Database Requirements

The page should support:

Create

Add a new roster member.

Read

Load existing roster members when the page opens.

Update

Edit a selected roster member.

Delete

Remove a roster member, preferably with a confirmation.

Refresh

Reload roster data from SQLite.

Team Support

Design for the fact that I eventually want multiple teams.

A player may belong to:

Core Team A
Core Team B
Achievement Team
Trial group
etc.

Do not hard-code a single roster.

If the existing project has a team model, use it.

If not, structure the database so we can add:

team
team_member

later without redesigning the roster.

Future Optimizer Compatibility

This is important.

The roster page is eventually going to feed an ESO raid-team optimization engine.

The future engine needs to be able to ask questions like:

Who can tank?
Who can heal?
Who can DD?
Who has multiple viable roles?
What classes are represented?
What sets/builds are available?
Who has experience with this trial?
Who has the required achievement?
Who is available?

Do not implement the optimizer yet.

But do not design the roster model in a way that prevents those questions later.

Existing Database Integration

Before creating any schema, inspect the current SQLite database and existing importers.

Use the same conventions already established elsewhere in the project.

If a schema migration system exists, use it.

If there isn't one, create the minimum necessary schema in the appropriate existing location rather than inventing a completely new database mechanism.

Existing UI Integration

Add the new page to the existing navigation/main window.

Do not create a second application window.

It should behave like the existing:

Broadcast
Field Notes
Achievements
Console
...

pages.

Deliverables

I want you to:

Inspect the existing architecture first.
Identify the files that need to be created or modified.
Explain briefly why each change is needed.
Implement the Roster page.
Implement the model/service/database integration.
Add the page to navigation.
Make sure the page can launch without breaking existing pages.
Test the database operations.
Tell me exactly how to run/test the new page.

Do not rewrite unrelated parts of the application.

Do not create duplicate database infrastructure.

Do not replace existing Foundry UI components unnecessarily.

Keep the implementation modular because this roster will eventually become an input to the ESO raid-team optimization engine.

One additional thing I'd tell Claude

After it finishes the first pass, don't immediately let it start adding gear/build/optimization functionality.

Get this milestone working first:

Roster Page
     ↓
Add Player
     ↓
SQLite
     ↓
Close app
     ↓
Reopen app
     ↓
Player still exists
     ↓
Edit Player
     ↓
SQLite updates

Once that works, we can expand the roster model into the genuinely interesting stuff.

And I'd make Team part of the initial schema even if the first UI only has a simple team selector. You already had the idea of storing team names in Settings for faster Broadcast entry, and the optimizer is eventually going to care about teams. Designing for that relationship now is much cheaper than discovering six months from now that every roster record assumed there could only ever be one team.